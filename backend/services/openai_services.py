"""
OpenAI Services for AI conversation management with advanced features
"""

import base64
import inspect
import time
from loguru import logger
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Union

import httpx
import tiktoken
from openai import AsyncOpenAI, OpenAI

from ..config import OPENAI_CONFIG, settings


class CircuitBreaker:
    """Simple circuit breaker to handle repeated API failures."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def call_allowed(self) -> bool:
        """Check if calls are allowed through the circuit breaker."""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker moved to HALF_OPEN state")
                return True
            return False
        else:  # HALF_OPEN
            return True

    def record_success(self):
        """Record a successful API call."""
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            self.failure_count = 0
            logger.info("Circuit breaker reset to CLOSED state")

    def record_failure(self):
        """Record a failed API call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(
                f"Circuit breaker OPENED after {self.failure_count} failures. "
                f"Will retry after {self.recovery_timeout} seconds."
            )


class OpenAIChatLLM:
    """Advanced OpenAI Chat LLM with circuit breaker, streaming, and multimodal support"""
    
    def __init__(
        self, 
        api_key: str = None, 
        model: str = None, 
        max_retries: int = 3,
        circuit_breaker_failure_threshold: int = 5,
        circuit_breaker_recovery_timeout: int = 60,
        http_connect_timeout: int = 30,
        http_read_timeout: int = 300,
        http_write_timeout: int = 30,
        http_pool_timeout: int = 30
    ) -> None:
        # Use config values with fallbacks
        self.api_key = api_key or OPENAI_CONFIG["api_key"]
        self.model = model or OPENAI_CONFIG["model"]
        self.max_tokens = OPENAI_CONFIG["max_tokens"]
        self.temperature = OPENAI_CONFIG["temperature"]
        self.max_retries = max_retries

        # Initialize circuit breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=circuit_breaker_failure_threshold,
            recovery_timeout=circuit_breaker_recovery_timeout,
        )

        # Create timeout configuration
        timeout_config = httpx.Timeout(
            connect=http_connect_timeout,
            read=http_read_timeout,
            write=http_write_timeout,
            pool=http_pool_timeout,
        )

        # Create custom httpx clients
        httpx_client = httpx.Client(
            timeout=timeout_config,
            limits=httpx.Limits(
                max_connections=100, max_keepalive_connections=20, keepalive_expiry=30.0
            ),
        )

        httpx_async_client = httpx.AsyncClient(
            timeout=timeout_config,
            limits=httpx.Limits(
                max_connections=100, max_keepalive_connections=20, keepalive_expiry=30.0
            ),
        )

        self.client = OpenAI(
            api_key=self.api_key,
            max_retries=max_retries,
            timeout=timeout_config,
            http_client=httpx_client,
        )
        self.async_client = AsyncOpenAI(
            api_key=self.api_key,
            max_retries=max_retries,
            timeout=timeout_config,
            http_client=httpx_async_client,
        )
        
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

        logger.info(
            f"Initialized OpenAI client with model: {self.model}, "
            f"timeouts: connect={http_connect_timeout}s, read={http_read_timeout}s, "
            f"write={http_write_timeout}s, pool={http_pool_timeout}s"
        )

    def _count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text string"""
        try:
            tokens = self.tokenizer.encode(text)
            return len(tokens)
        except Exception as e:
            logger.warning(f"Error counting tokens: {e}")
            # Fallback to a rough estimate
            return len(text) // 4

    def _process_images_for_content(
        self, images: List[str], detail: str = "low"
    ) -> List[Dict[str, Any]]:
        """
        Process images for OpenAI Vision API content format.
        All images should be in base64 data URL format: data:image/jpeg;base64,{base64_image}

        Args:
            images: List of base64 data URLs (e.g., "data:image/jpeg;base64,...")
            detail: Level of detail for image processing

        Returns:
            List of image content dictionaries
        """
        image_contents = []

        for i, image in enumerate(images):
            try:
                # Validate base64 data URL format
                if not image.startswith("data:image/"):
                    logger.warning(
                        f"Image {i + 1} is not in expected base64 data URL format: {image[:50]}..."
                    )
                    continue

                # Ensure it contains base64 data
                if ";base64," not in image:
                    logger.warning(
                        f"Image {i + 1} does not contain base64 data: {image[:50]}..."
                    )
                    continue

                # Extract and validate base64 data
                try:
                    _, base64_part = image.split(";base64,", 1)
                    if not base64_part.strip():
                        logger.warning(f"Image {i + 1} has empty base64 data")
                        continue

                    # Validate base64 format (basic check)
                    base64.b64decode(base64_part, validate=True)

                except (ValueError, Exception) as decode_error:
                    logger.warning(
                        f"Image {i + 1} has invalid base64 data: {decode_error}"
                    )
                    continue

                image_content = {
                    "type": "image_url",
                    "image_url": {"url": image, "detail": detail},
                }

                image_contents.append(image_content)
                logger.debug(
                    f"Successfully processed image {i + 1} (base64 length: {len(image)})"
                )

            except Exception as e:
                logger.error(f"Error processing image {i + 1}: {e}")
                continue

        logger.info(
            f"Processed {len(image_contents)} out of {len(images)} images successfully"
        )
        return image_contents

    def _create_messages(
        self,
        query: str,
        system_prompt: str = None,
        history: List[Dict[str, str]] = None,
        rag_context: Optional[str] = "",
        memories: Optional[str] = "",
        images: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Dict[str, Union[List[Dict[str, str]], int]]:
        """
        Create messages for OpenAI API with support for multimodal content
        
        Args:
            query: User's question or message
            system_prompt: System prompt to use
            history: Conversation history
            rag_context: RAG context information
            memories: User memory context
            images: List of base64 image URLs
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with messages and token counts
        """
        
        # Default system prompt if none provided
        if system_prompt is None:
            system_prompt = """You are an AI assistant for Dextrends, a leading technology company specializing in digital financial services and blockchain solutions. 

Your role is to help users understand Dextrends' offerings and provide personalized assistance. You should:

1. Be knowledgeable about Dextrends' services including:
   - Digital financial services
   - Blockchain solutions
   - Financial technology products
   - Digital payment systems
   - Cryptocurrency services

2. Provide accurate, helpful, and professional responses
3. Personalize responses based on user preferences and conversation history
4. Ask clarifying questions when needed
5. Be friendly and approachable while maintaining professionalism
6. Direct users to appropriate resources or contact information when necessary

Remember to always represent Dextrends positively and provide value to users."""

        def create_rag_context(rag_context: str) -> str:
            """Create RAG context string if provided."""
            return (
                f"""Use the following **Relevant Context** to answer the user's question. \
If **Relevant Context** does not contain relevant information to user's question, just answer without using **Relevant Context**.

**Relevant Context**:
{rag_context}
"""
                if rag_context
                else ""
            )

        try:
            has_images = images and len(images) > 0
            
            # Count prompt tokens
            system_tokens = self._count_tokens(system_prompt)
            user_tokens = self._count_tokens(query)
            total_prompt_tokens = system_tokens + user_tokens

            # Construct messages
            messages = [{"role": "system", "content": system_prompt}]

            if memories:
                messages.append(
                    {
                        "role": "assistant",
                        "content": f"Related long-term memory and user information: {memories}",
                    }
                )

            # Add conversation history
            if history:
                for item in history:
                    if isinstance(item, dict) and 'role' in item and 'content' in item:
                        messages.append({"role": item['role'], "content": item['content']})
                    elif hasattr(item, 'role') and hasattr(item, 'content'):
                        messages.append({"role": item.role, "content": item.content})

            # Create user message with potential multimodal content
            rag_context_str = create_rag_context(rag_context)
            user_query = f"{rag_context_str}\n\nQuestion: {query}".strip()
            
            if has_images:
                # Create multimodal content with text and images
                if not user_query:
                    user_query = "Please describe the provided images."
                user_content = [{"type": "text", "text": user_query}]
                image_detail = kwargs.get("image_detail", "low")
                user_content.extend(
                    self._process_images_for_content(images, image_detail)
                )
            else:
                # Text-only content
                user_content = user_query

            messages.append({"role": "user", "content": user_content})
            logger.info(f"Created Messages: {messages}")

            logger.info(
                f"LLM Messages created with {len(messages)} messages, images: {has_images}"
            )
            return {
                "messages": messages,
                "total_prompt_tokens": total_prompt_tokens,
                "system_tokens": system_tokens,
                "user_tokens": user_tokens,
            }

        except Exception as e:
            import traceback

            logger.error(
                f"Error creating OpenAI messages: {e}\n{traceback.format_exc()}"
            )
            return {
                "error": str(e),
                "error_type": "message_creation_error",
                "messages": [],
                "total_prompt_tokens": 0,
                "system_tokens": 0,
                "user_tokens": 0,
            }

    def chat_completion(self, messages: list, **kwargs) -> Dict[str, Any]:
        """Synchronous chat completion"""
        start_time = time.time()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=kwargs.get('max_tokens', self.max_tokens),
                temperature=kwargs.get('temperature', self.temperature),
                timeout=kwargs.get('timeout', 300),
                **kwargs,
            )
            end_time = time.time()
            response_time = end_time - start_time
            completion = response.choices[0].message.content
            completion_tokens = response.usage.completion_tokens
            return {
                "response_time": response_time,
                "completion": completion,
                "completion_tokens": completion_tokens,
                "success": True,
            }

        except Exception as e:
            import traceback

            logger.error(
                f"Error in OpenAI chat_completion (max_retries: {self.max_retries}): {e}\n{traceback.format_exc()}"
            )
            end_time = time.time()
            return {
                "error": str(e),
                "error_type": "chat_completion_error",
                "response_time": end_time - start_time,
                "completion": None,
                "completion_tokens": 0,
                "success": False,
            }

    async def achat_completion(self, messages: list, **kwargs) -> Dict[str, Any]:
        """Asynchronous chat completion"""
        start_time = time.time()
        try:
            response = await self.async_client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=kwargs.get('max_tokens', self.max_tokens),
                temperature=kwargs.get('temperature', self.temperature),
                timeout=kwargs.get('timeout', 300),
                **kwargs,
            )
            end_time = time.time()
            response_time = end_time - start_time
            completion = response.choices[0].message.content
            completion_tokens = response.usage.completion_tokens
            return {
                "response_time": response_time,
                "completion": completion,
                "completion_tokens": completion_tokens,
                "success": True,
            }
        except Exception as e:
            import traceback

            logger.error(
                f"Error in OpenAI achat_completion (max_retries: {self.max_retries}): {e}\n{traceback.format_exc()}"
            )
            end_time = time.time()
            return {
                "error": str(e),
                "error_type": "async_chat_completion_error",
                "response_time": end_time - start_time,
                "completion": None,
                "completion_tokens": 0,
                "success": False,
            }

    async def stream_chat_completion(
        self, messages: list, **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion from OpenAI API with improved timeout handling and circuit breaker."""
        import httpx
        import openai

        # Check circuit breaker before making the call
        if not self.circuit_breaker.call_allowed():
            error_msg = (
                "Service temporarily unavailable due to repeated failures. "
                "Please try again in a few minutes."
            )
            logger.warning(f"Circuit breaker blocked request: {error_msg}")
            yield f"Error: {error_msg}"
            return

        start_time = time.time()
        chunk_count = 0
        completion_text = ""
        success = False

        try:
            stream = await self.async_client.chat.completions.create(
                model=self.model, 
                messages=messages, 
                stream=True,
                max_tokens=kwargs.get('max_tokens', self.max_tokens),
                temperature=kwargs.get('temperature', self.temperature),
                **kwargs
            )

            async for chunk in stream:
                if chunk.choices:
                    content = chunk.choices[0].delta.content
                    if content:
                        completion_text += content
                        chunk_count += 1
                        success = True
                        yield content

            # Log successful completion and record success
            if success:
                self.circuit_breaker.record_success()
                completion_tokens = self._count_tokens(completion_text)
                end_time = time.time()
                response_time = end_time - start_time
                logger.info(
                    f"Streamed completion successful: {len(completion_text)} chars, {chunk_count} chunks, "
                    f"tokens: {completion_tokens}, time: {response_time:.2f}s, max_retries: {self.max_retries}"
                )

        except httpx.ReadTimeout as read_timeout_error:
            self.circuit_breaker.record_failure()
            logger.error(
                f"HTTP read timeout during streaming after {chunk_count} chunks, "
                f"{len(completion_text)} chars received: {read_timeout_error}"
            )
            error_msg = (
                f"Stream interrupted due to timeout. Received {chunk_count} chunks "
                f"({len(completion_text)} characters) before timeout."
            )
            yield f"Error: {error_msg}"

        except httpx.ConnectTimeout as connect_timeout_error:
            self.circuit_breaker.record_failure()
            logger.error(
                f"HTTP connect timeout during streaming: {connect_timeout_error}"
            )
            yield "Error: Connection timeout - unable to connect to API service"

        except openai.APITimeoutError as api_timeout_error:
            self.circuit_breaker.record_failure()
            logger.error(
                f"OpenAI API timeout during streaming after {chunk_count} chunks: {api_timeout_error}"
            )
            error_msg = (
                f"API timeout after {chunk_count} chunks. "
                "Try reducing prompt complexity or retry later."
            )
            yield f"Error: {error_msg}"

        except openai.APIConnectionError as connection_error:
            self.circuit_breaker.record_failure()
            logger.error(
                f"OpenAI API connection error during streaming: {connection_error}"
            )
            yield "Error: API connection failed - service may be temporarily unavailable"

        except openai.RateLimitError as rate_limit_error:
            # Don't record failure for rate limits as it's not a service issue
            logger.error(f"Rate limit exceeded during streaming: {rate_limit_error}")
            yield "Error: Rate limit exceeded - please wait before trying again"

        except Exception as e:
            import traceback

            error_type = type(e).__name__

            # Record failure for network/timeout related errors
            if any(
                keyword in str(e).lower()
                for keyword in ["timeout", "connection", "network"]
            ):
                self.circuit_breaker.record_failure()

            logger.error(
                f"Error in OpenAI stream_chat_completion ({error_type}) after {chunk_count} chunks, "
                f"max_retries: {self.max_retries}: {e}\n{traceback.format_exc()}"
            )

            # Provide more specific error messages based on error type
            if "httpx" in str(type(e)).lower():
                error_msg = f"Network error during streaming: {str(e)}"
            elif "timeout" in str(e).lower():
                error_msg = (
                    f"Timeout during streaming after {chunk_count} chunks: {str(e)}"
                )
            else:
                error_msg = f"Streaming error: {str(e)}"

            yield f"Error: {error_msg}"

    async def stream_chat_completion_callback(
        self, messages: list, callback: Callable[[str], None], **kwargs
    ):
        """Stream chat completion with a callback function and circuit breaker protection."""

        # Check circuit breaker
        if not self.circuit_breaker.call_allowed():
            error_msg = (
                "Service temporarily unavailable due to repeated failures. "
                "Please try again in a few minutes."
            )
            logger.warning(f"Circuit breaker blocked callback request: {error_msg}")

            # Send error through callback
            is_async_callback = inspect.iscoroutinefunction(callback)
            try:
                if is_async_callback:
                    await callback(f"Error: {error_msg}")
                else:
                    callback(f"Error: {error_msg}")
            except Exception as callback_error:
                logger.warning(
                    f"Failed to send circuit breaker error through callback: {callback_error}"
                )

            return {
                "completion": f"Error: {error_msg}",
                "error": error_msg,
                "error_type": "circuit_breaker_open",
                "processing_time": 0,
                "completion_tokens": 0,
                "success": False,
                "callback_failed": False,
            }

        start_time = time.time()
        is_async_callback = inspect.iscoroutinefunction(callback)
        callback_failed = False

        try:
            completion_text = ""
            stream_generator = self.stream_chat_completion(messages=messages, **kwargs)
            # Stream the completion
            async for chunk in stream_generator:
                # Check if this is an error message from circuit breaker or streaming issues
                if chunk.startswith("Error:"):
                    # Send error through callback and return early
                    if not callback_failed:
                        try:
                            if is_async_callback:
                                await callback(chunk)
                            else:
                                callback(chunk)
                        except Exception as callback_error:
                            logger.warning(
                                f"Callback failed for error message: {callback_error}"
                            )
                            callback_failed = True

                    return {
                        "completion": chunk,
                        "error": chunk,
                        "error_type": "stream_callback_error",
                        "processing_time": time.time() - start_time,
                        "completion_tokens": 0,
                        "success": False,
                        "callback_failed": callback_failed,
                    }

                completion_text += chunk

                # Only continue calling callback if it hasn't failed
                if not callback_failed:
                    try:
                        # Handle both sync and async callbacks
                        if is_async_callback:
                            await callback(chunk)
                        else:
                            callback(chunk)
                    except Exception as callback_error:
                        logger.warning(
                            f"Callback failed for chunk, stopping further calls: {callback_error}"
                        )
                        callback_failed = True
                        # Continue processing but don't call callback anymore

            completion_tokens = self._count_tokens(completion_text)
            logger.info(
                f"Streamed completion with callback: {completion_text} (tokens: {completion_tokens}, max_retries: {self.max_retries})"
            )
            end_time = time.time()
            response_time = end_time - start_time
            # Return result metadata
            return {
                "completion": completion_text,
                "completion_tokens": completion_tokens,
                "processing_time": response_time,
                "success": True,
                "callback_failed": callback_failed,
            }
        except Exception as e:
            import traceback

            logger.error(
                f"Error in OpenAI stream_chat_completion_callback (max_retries: {self.max_retries}): {e}\n{traceback.format_exc()}"
            )
            error_message = f"I'm sorry, I encountered an error: {str(e)}"

            # Only try to send error message if callback hasn't already failed
            if not callback_failed:
                try:
                    if is_async_callback:
                        await callback(error_message)
                    else:
                        callback(error_message)
                except Exception as callback_error:
                    logger.warning(
                        f"Failed to send error message through callback: {callback_error}"
                    )

            return {
                "completion": error_message,
                "error": str(e),
                "error_type": "stream_callback_error",
                "processing_time": time.time() - start_time,
                "completion_tokens": 0,
                "success": False,
                "callback_failed": True,
            }