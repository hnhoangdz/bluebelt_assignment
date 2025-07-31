"""
Embedding service for Dextrends AI Chatbot
Handles text embedding generation and vector operations
"""

import asyncio
import json
from typing import List, Dict, Any, Optional
import hashlib
import logging
import uuid

import openai
from ..config import settings
from ..core.qdrant_client import get_qdrant_client

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Service for generating and managing embeddings"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.openai_api_key)
        self.embedding_model = "text-embedding-3-small"  # More cost-effective
        self.embedding_dimension = 1536
        
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a given text"""
        try:
            # Clean and prepare text
            cleaned_text = self._clean_text(text)
            
            # Generate embedding using OpenAI
            response = await asyncio.to_thread(
                self.client.embeddings.create,
                model=self.embedding_model,
                input=cleaned_text
            )
            
            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding for text of length {len(cleaned_text)}")
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    async def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        try:
            # Clean texts
            cleaned_texts = [self._clean_text(text) for text in texts]
            
            # Generate embeddings in batch (more efficient)
            response = await asyncio.to_thread(
                self.client.embeddings.create,
                model=self.embedding_model,
                input=cleaned_texts
            )
            
            embeddings = [data.embedding for data in response.data]
            logger.info(f"Generated {len(embeddings)} embeddings")
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise
    
    def _clean_text(self, text: str) -> str:
        """Clean and prepare text for embedding"""
        if not text:
            return ""
        
        # Remove excessive whitespace and normalize
        cleaned = ' '.join(text.strip().split())
        
        # Truncate if too long (OpenAI has token limits)
        max_length = 8000  # Conservative limit
        if len(cleaned) > max_length:
            cleaned = cleaned[:max_length]
            logger.warning(f"Text truncated from {len(text)} to {len(cleaned)} characters")
        
        return cleaned
    
    def _generate_point_id(self, content: str, source: str = "") -> str:
        """Generate a unique UUID for a vector point"""
        # Generate a UUID based on content hash for reproducibility
        content_hash = hashlib.md5(f"{source}:{content}".encode()).hexdigest()
        # Create a UUID from the hash 
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, content_hash))
    
    async def embed_company_offerings(self, offerings_file: str) -> bool:
        """Process and embed company offerings data"""
        try:
            # Load company offerings data
            with open(offerings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Get Qdrant client
            qdrant_client = await get_qdrant_client()
            
            # Process company info
            company_info = data.get('company_info', {})
            points = []
            
            # Embed company overview
            company_text = f"""
            Company: {company_info.get('name', '')}
            Description: {company_info.get('description', '')}
            Mission: {company_info.get('mission', '')}
            Established: {company_info.get('established', '')}
            Headquarters: {company_info.get('headquarters', '')}
            Global Presence: {', '.join(company_info.get('global_presence', []))}
            Expertise: {', '.join(company_info.get('expertise', []))}
            """
            
            company_embedding = await self.generate_embedding(company_text.strip())
            points.append({
                "id": self._generate_point_id(company_text, "company_info"),
                "vector": company_embedding,
                "payload": {
                    "type": "company_info",
                    "title": f"{company_info.get('name', '')} Company Overview",
                    "content": company_text.strip(),
                    "category": "company_info",
                    "source": "company_data",
                    **company_info
                }
            })
            
            # Process each service
            services = data.get('services', [])
            for service in services:
                # Create comprehensive text for embedding
                service_text = f"""
                Service: {service.get('title', '')}
                Category: {service.get('category', '')}
                Description: {service.get('description', '')}
                Features: {', '.join(service.get('features', []))}
                Benefits: {', '.join(service.get('benefits', []))}
                Use Cases: {', '.join(service.get('use_cases', []))}
                Pricing: {service.get('pricing', '')}
                """
                
                # Generate embedding
                service_embedding = await self.generate_embedding(service_text.strip())
                
                # Create point
                points.append({
                    "id": self._generate_point_id(service_text, f"service_{service.get('id', '')}"),
                    "vector": service_embedding,
                    "payload": {
                        "type": "service",
                        "service_id": service.get('id', ''),
                        "title": service.get('title', ''),
                        "category": service.get('category', ''),
                        "content": service_text.strip(),
                        "source": "company_offerings",
                        **service
                    }
                })
            
            # Store embeddings in Qdrant
            success = await qdrant_client.add_points("company_offerings", points)
            
            if success:
                logger.info(f"Successfully embedded {len(points)} company offering points")
                return True
            else:
                logger.error("Failed to store company offering embeddings")
                return False
                
        except Exception as e:
            logger.error(f"Failed to embed company offerings: {e}")
            return False
    
    async def embed_faq_data(self, faq_file: str) -> bool:
        """Process and embed FAQ data"""
        try:
            # Load FAQ data
            with open(faq_file, 'r', encoding='utf-8') as f:
                faq_data = json.load(f)
            
            # Get Qdrant client
            qdrant_client = await get_qdrant_client()
            
            points = []
            
            # Process each FAQ
            for faq in faq_data:
                # Create comprehensive text for embedding
                faq_text = f"""
                Question: {faq.get('question', '')}
                Answer: {faq.get('answer', '')}
                Category: {faq.get('category', '')}
                Keywords: {', '.join(faq.get('keywords', []))}
                """
                
                # Generate embedding
                faq_embedding = await self.generate_embedding(faq_text.strip())
                
                # Create point
                points.append({
                    "id": self._generate_point_id(faq_text, f"faq_{faq.get('id', '')}"),
                    "vector": faq_embedding,
                    "payload": {
                        "type": "faq",
                        "faq_id": faq.get('id', ''),
                        "question": faq.get('question', ''),
                        "answer": faq.get('answer', ''),
                        "category": faq.get('category', ''),
                        "keywords": faq.get('keywords', []),
                        "content": faq_text.strip(),
                        "source": "faq_data"
                    }
                })
            
            # Store embeddings in Qdrant
            success = await qdrant_client.add_points("faq", points)
            
            if success:
                logger.info(f"Successfully embedded {len(points)} FAQ points")
                return True
            else:
                logger.error("Failed to store FAQ embeddings")
                return False
                
        except Exception as e:
            logger.error(f"Failed to embed FAQ data: {e}")
            return False
    
    async def search_similar_content(
        self, 
        query: str, 
        collection_type: str = "both",
        limit: int = 5,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search for similar content across collections"""
        try:
            # Generate query embedding
            query_embedding = await self.generate_embedding(query)
            
            # Get Qdrant client
            qdrant_client = await get_qdrant_client()
            
            results = []
            
            # Search in specified collections
            if collection_type in ["both", "offerings"]:
                offerings_results = await qdrant_client.search(
                    "company_offerings", 
                    query_embedding, 
                    limit=limit,
                    score_threshold=score_threshold
                )
                results.extend(offerings_results)
            
            if collection_type in ["both", "faq"]:
                faq_results = await qdrant_client.search(
                    "faq", 
                    query_embedding, 
                    limit=limit,
                    score_threshold=score_threshold
                )
                results.extend(faq_results)
            
            # Sort by score (highest first)
            results.sort(key=lambda x: x["score"], reverse=True)
            
            # Return top results
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Failed to search similar content: {e}")
            return []
    
    async def initialize_embeddings(self, force_refresh: bool = False) -> bool:
        """Initialize all embeddings from data files"""
        try:
            # Get Qdrant client
            qdrant_client = await get_qdrant_client()
            
            # If force refresh, delete existing collections
            if force_refresh:
                logger.info("Force refresh requested, recreating collections...")
                try:
                    await asyncio.to_thread(
                        qdrant_client.client.delete_collection,
                        collection_name="dextrends_offerings"
                    )
                    logger.info("Deleted existing company offerings collection")
                except Exception as e:
                    logger.debug(f"Could not delete offerings collection: {e}")
                
                try:
                    await asyncio.to_thread(
                        qdrant_client.client.delete_collection,
                        collection_name="dextrends_faq"
                    )
                    logger.info("Deleted existing FAQ collection")
                except Exception as e:
                    logger.debug(f"Could not delete FAQ collection: {e}")
            else:
                # Check if collections have data
                offerings_info = await qdrant_client.get_collection_info("company_offerings")
                faq_info = await qdrant_client.get_collection_info("faq")
                
                if (offerings_info.get("points_count", 0) > 0 and 
                    faq_info.get("points_count", 0) > 0):
                    logger.info("Embeddings already exist, skipping initialization")
                    return True
            
            # Initialize company offerings embeddings  
            offerings_success = await self.embed_company_offerings(
                "/app/data/company_offerings.json"
            )
            
            # Initialize FAQ embeddings
            faq_success = await self.embed_faq_data(
                "/app/data/faq_data.json"
            )
            
            if offerings_success and faq_success:
                logger.info("Successfully initialized all embeddings")
                return True
            else:
                logger.error("Failed to initialize some embeddings")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize embeddings: {e}")
            return False


# Global embedding service instance
embedding_service = EmbeddingService()

async def get_embedding_service() -> EmbeddingService:
    """Get the global embedding service instance"""
    return embedding_service