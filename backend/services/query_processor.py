"""
Query Processing Service for Dextrends AI Chatbot
Handles query rewriting, intent classification, and routing
"""

import asyncio
import json
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import logging

import openai
from ..config import settings

logger = logging.getLogger(__name__)

class QueryIntent(Enum):
    """Query intent categories"""
    COMPANY_INFO = "company_info"
    SERVICE_INQUIRY = "service_inquiry"
    PRICING = "pricing"
    TECHNICAL_SUPPORT = "technical_support"
    INTEGRATION = "integration"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    GENERAL_FAQ = "general_faq"
    GREETING = "greeting"
    GOODBYE = "goodbye"
    UNKNOWN = "unknown"

class QueryType(Enum):
    """Query type for collection routing"""
    OFFERING = "offering"  # Company services/offerings related
    FAQ = "faq"           # Frequently asked questions  
    BOTH = "both"         # Needs both offering and FAQ info
    GENERAL = "general"   # General queries not specific

class QueryProcessor:
    """Service for processing and routing user queries"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.openai_api_key)
    
    async def rewrite_query(
        self, 
        user_query: str, 
        conversation_history: List[Dict[str, str]] = None
    ) -> str:
        """
        Rewrite user query for better retrieval, considering conversation context
        """
        try:
            # Build context from conversation history
            context = ""
            if conversation_history:
                # Get last 3-5 messages for context
                recent_messages = conversation_history[-5:]
                context_parts = []
                for msg in recent_messages:
                    role = msg.get('role', 'user')
                    content = msg.get('content', '')
                    context_parts.append(f"{role}: {content}")
                context = "\n".join(context_parts)
            
            # Query rewriting prompt
            system_prompt = """You are a query rewriting expert for a financial technology and blockchain company (Dextrends). 
            Your task is to rewrite user queries to be more specific, clear, and suitable for semantic search.
            
            Guidelines:
            1. Expand abbreviations and technical terms
            2. Add relevant context from conversation history if provided
            3. Make implicit questions explicit
            4. Preserve the original intent
            5. Focus on Dextrends services: digital payments, blockchain, DeFi, smart contracts, asset management, etc.
            6. If the query is already clear and specific, return it as is
            
            Return only the rewritten query, nothing else."""
            
            user_prompt = f"""
            Original query: {user_query}
            
            Conversation context:
            {context if context else "No previous conversation context"}
            
            Rewrite this query for better semantic search:"""
            
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=150,
                temperature=0.3
            )
            
            rewritten_query = response.choices[0].message.content.strip()
            
            logger.info(f"Query rewritten: '{user_query}' -> '{rewritten_query}'")
            return rewritten_query
            
        except Exception as e:
            logger.error(f"Failed to rewrite query: {e}")
            return user_query  # Fallback to original query
    
    async def classify_intent(self, query: str) -> Tuple[QueryIntent, float]:
        """
        Classify the intent of a user query
        Returns intent and confidence score
        """
        try:
            system_prompt = """You are an intent classification expert for Dextrends, a financial technology and blockchain company.
            
            Classify user queries into one of these intents:
            - company_info: Questions about company, history, mission, team
            - service_inquiry: Questions about specific services or capabilities
            - pricing: Questions about costs, fees, pricing models
            - technical_support: Technical issues, troubleshooting, how-to questions
            - integration: Questions about APIs, integrations, implementation
            - security: Security-related questions, compliance, safety
            - compliance: Regulatory, legal, compliance questions
            - general_faq: General frequently asked questions
            - greeting: Greetings, introductions
            - goodbye: Farewells, ending conversation
            - unknown: Cannot determine intent
            
            Respond in JSON format: {"intent": "intent_name", "confidence": 0.95}
            Confidence should be between 0.0 and 1.0."""
            
            user_prompt = f"Classify this query: {query}"
            
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=50,
                temperature=0.1
            )
            
            result = json.loads(response.choices[0].message.content.strip())
            intent_str = result.get("intent", "unknown")
            confidence = float(result.get("confidence", 0.5))
            
            # Convert string to enum
            try:
                intent = QueryIntent(intent_str)
            except ValueError:
                intent = QueryIntent.UNKNOWN
                confidence = 0.3
            
            logger.info(f"Intent classified: {intent.value} (confidence: {confidence:.2f})")
            return intent, confidence
            
        except Exception as e:
            logger.error(f"Failed to classify intent: {e}")
            return QueryIntent.UNKNOWN, 0.3
    
    async def classify_query_type(self, query: str, intent: QueryIntent) -> Tuple[QueryType, float]:
        """
        Classify query type for collection routing (offering/faq/both/general)
        Returns query type and confidence score
        """
        try:
            system_prompt = """You are a query classification expert for Dextrends, a financial technology and blockchain company.

            Your task is to classify user queries to determine which knowledge collections to search:

            **OFFERING**: Queries about company services, products, solutions, capabilities, features
            - Examples: "What services does Dextrends offer?", "Tell me about your payment solutions", "What blockchain services do you provide?"
            
            **FAQ**: Common questions, general inquiries, how-to questions, support queries
            - Examples: "How secure are your solutions?", "What payment methods do you support?", "How does integration work?"
            
            **BOTH**: Complex queries that need both service info and FAQ knowledge
            - Examples: "What are your payment solutions and how much do they cost?", "Tell me about blockchain services and security"
            
            **GENERAL**: Greetings, conversations, or queries not requiring specific knowledge
            - Examples: "Hello", "Thanks", "How are you?", unclear questions

            Respond in JSON format: {"query_type": "offering|faq|both|general", "confidence": 0.95}
            Confidence should be between 0.0 and 1.0."""
            
            user_prompt = f"""
            Query: {query}
            Intent: {intent.value}
            
            Classify the query type for collection routing:"""
            
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=100,
                temperature=0.1
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Clean up JSON response (remove code blocks if present)
            if response_text.startswith("```json"):
                response_text = response_text[7:]  # Remove "```json"
            if response_text.endswith("```"):
                response_text = response_text[:-3]  # Remove "```"
            response_text = response_text.strip()
            
            # Try to parse JSON response
            try:
                result = json.loads(response_text)
                query_type_str = result.get("query_type", "general")
                confidence = float(result.get("confidence", 0.5))
            except json.JSONDecodeError:
                # Fallback: try to extract from response text
                logger.warning(f"Failed to parse JSON response: {response_text}")
                if "offering" in response_text.lower():
                    query_type_str = "offering"
                    confidence = 0.7
                elif "faq" in response_text.lower():
                    query_type_str = "faq"
                    confidence = 0.7
                elif "both" in response_text.lower():
                    query_type_str = "both"
                    confidence = 0.7
                else:
                    query_type_str = "general"
                    confidence = 0.5
            
            # Convert string to enum
            try:
                query_type = QueryType(query_type_str)
            except ValueError:
                query_type = QueryType.GENERAL
                confidence = 0.3
            
            logger.info(f"Query type classified: {query_type.value} (confidence: {confidence:.2f})")
            return query_type, confidence
            
        except Exception as e:
            logger.error(f"Failed to classify query type: {e}")
            return QueryType.GENERAL, 0.3
    
    def route_query(self, intent: QueryIntent, query_type: QueryType, confidence: float) -> Dict[str, Any]:
        """
        Route query based on intent classification
        Returns routing decision with parameters
        """
        try:
            # Default routing configuration based on query type
            if query_type == QueryType.OFFERING:
                default_collections = ["offerings"]
            elif query_type == QueryType.FAQ:
                default_collections = ["faq"]
            elif query_type == QueryType.BOTH:
                default_collections = ["both"]
            else:  # GENERAL
                default_collections = ["both"]
            
            routing_config = {
                "use_rag": True,
                "search_collections": default_collections,
                "search_limit": 5,
                "score_threshold": 0.4,  # Lowered threshold for better recall
                "response_style": "informative",
                "include_sources": True,
                "escalate_to_human": False
            }
            
            # Intent-specific routing
            if intent == QueryIntent.COMPANY_INFO:
                routing_config.update({
                    "search_collections": ["offerings"],
                    "search_limit": 3,
                    "response_style": "professional",
                    "score_threshold": 0.4
                })
            
            elif intent == QueryIntent.SERVICE_INQUIRY:
                routing_config.update({
                    "search_collections": ["offerings"],
                    "search_limit": 5,
                    "response_style": "detailed",
                    "score_threshold": 0.4
                })
            
            elif intent == QueryIntent.PRICING:
                routing_config.update({
                    "search_collections": ["both"],
                    "search_limit": 4,
                    "response_style": "precise",
                    "score_threshold": 0.4
                })
            
            elif intent == QueryIntent.TECHNICAL_SUPPORT:
                routing_config.update({
                    "search_collections": ["faq"],
                    "search_limit": 6,
                    "response_style": "step_by_step",
                    "score_threshold": 0.4,
                    "escalate_to_human": confidence < 0.7
                })
            
            elif intent == QueryIntent.INTEGRATION:
                routing_config.update({
                    "search_collections": ["both"],
                    "search_limit": 5,
                    "response_style": "technical",
                    "score_threshold": 0.7
                })
            
            elif intent in [QueryIntent.SECURITY, QueryIntent.COMPLIANCE]:
                routing_config.update({
                    "search_collections": ["both"],
                    "search_limit": 4,
                    "response_style": "authoritative",
                    "score_threshold": 0.8
                })
            
            elif intent == QueryIntent.GENERAL_FAQ:
                routing_config.update({
                    "search_collections": ["faq"],
                    "search_limit": 5,
                    "response_style": "conversational",
                    "score_threshold": 0.65
                })
            
            elif intent == QueryIntent.GREETING:
                routing_config.update({
                    "use_rag": False,
                    "response_style": "friendly",
                    "search_collections": []
                })
            
            elif intent == QueryIntent.GOODBYE:
                routing_config.update({
                    "use_rag": False,
                    "response_style": "polite",
                    "search_collections": []
                })
            
            elif intent == QueryIntent.UNKNOWN:
                routing_config.update({
                    "search_collections": ["both"],
                    "search_limit": 3,
                    "response_style": "helpful",
                    "score_threshold": 0.6,
                    "escalate_to_human": confidence < 0.4
                })
            
            # Add metadata
            routing_config.update({
                "intent": intent.value,
                "query_type": query_type.value,
                "confidence": confidence,
                "timestamp": asyncio.get_event_loop().time()
            })
            
            logger.info(f"Query routed for intent {intent.value}: {routing_config}")
            return routing_config
            
        except Exception as e:
            logger.error(f"Failed to route query: {e}")
            # Fallback routing
            return {
                "use_rag": True,
                "search_collections": ["both"],
                "search_limit": 3,
                "score_threshold": 0.6,
                "response_style": "helpful",
                "include_sources": True,
                "escalate_to_human": False,
                "intent": "unknown",
                "query_type": "general",
                "confidence": 0.3
            }
    
    async def enhance_query_with_keywords(self, query: str, intent: QueryIntent) -> str:
        """
        Enhance query with relevant keywords based on intent
        """
        try:
            # Intent-specific keyword mappings
            keyword_mappings = {
                QueryIntent.COMPANY_INFO: [
                    "Dextrends", "company", "about", "mission", "history", "team"
                ],
                QueryIntent.SERVICE_INQUIRY: [
                    "services", "solutions", "platform", "features", "capabilities"
                ],
                QueryIntent.PRICING: [
                    "cost", "price", "fee", "pricing", "rates", "charges", "subscription"
                ],
                QueryIntent.TECHNICAL_SUPPORT: [
                    "help", "support", "troubleshooting", "issue", "problem", "how to"
                ],
                QueryIntent.INTEGRATION: [
                    "API", "integration", "connect", "implement", "setup", "developer"
                ],
                QueryIntent.SECURITY: [
                    "security", "safe", "encryption", "protection", "secure", "safety"
                ],
                QueryIntent.COMPLIANCE: [
                    "compliance", "regulatory", "legal", "KYC", "AML", "regulation"
                ]
            }
            
            # Get relevant keywords
            keywords = keyword_mappings.get(intent, [])
            
            if not keywords:
                return query
            
            # Check which keywords are missing from the query
            query_lower = query.lower()
            missing_keywords = [kw for kw in keywords if kw.lower() not in query_lower]
            
            # Add up to 2 most relevant missing keywords
            if missing_keywords:
                enhanced_query = f"{query} {' '.join(missing_keywords[:2])}"
                logger.debug(f"Enhanced query with keywords: {enhanced_query}")
                return enhanced_query
            
            return query
            
        except Exception as e:
            logger.error(f"Failed to enhance query with keywords: {e}")
            return query
    
    async def process_query(
        self, 
        user_query: str, 
        conversation_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Complete query processing pipeline
        """
        try:
            # Step 1: Rewrite query for better retrieval
            rewritten_query = await self.rewrite_query(user_query, conversation_history)
            
            # Step 2: Classify intent
            intent, confidence = await self.classify_intent(rewritten_query)
            
            # Step 3: Classify query type for collection routing
            query_type, type_confidence = await self.classify_query_type(rewritten_query, intent)
            
            # Step 4: Enhance with keywords
            enhanced_query = await self.enhance_query_with_keywords(rewritten_query, intent)
            
            # Step 5: Route query
            routing_config = self.route_query(intent, query_type, confidence)
            
            # Compile results
            processing_result = {
                "original_query": user_query,
                "rewritten_query": rewritten_query,
                "enhanced_query": enhanced_query,
                "intent": intent.value,
                "intent_confidence": confidence,
                "query_type": query_type.value,
                "type_confidence": type_confidence,
                "routing": routing_config,
                "processing_metadata": {
                    "has_context": bool(conversation_history),
                    "context_length": len(conversation_history) if conversation_history else 0,
                    "processing_time": asyncio.get_event_loop().time()
                }
            }
            
            logger.info(f"Query processing completed for: {user_query}")
            return processing_result
            
        except Exception as e:
            logger.error(f"Failed to process query: {e}")
            # Return minimal fallback
            return {
                "original_query": user_query,
                "rewritten_query": user_query,
                "enhanced_query": user_query,
                "intent": QueryIntent.UNKNOWN.value,
                "intent_confidence": 0.3,
                "query_type": QueryType.GENERAL.value,
                "type_confidence": 0.3,
                "routing": {
                    "use_rag": True,
                    "search_collections": ["both"],
                    "search_limit": 3,
                    "score_threshold": 0.6,
                    "response_style": "helpful",
                    "intent": "unknown",
                    "query_type": "general",
                    "confidence": 0.3
                }
            }


# Global query processor instance
query_processor = QueryProcessor()

async def get_query_processor() -> QueryProcessor:
    """Get the global query processor instance"""
    return query_processor