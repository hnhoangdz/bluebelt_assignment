"""
Qdrant vector database client for Dextrends AI Chatbot
"""

import asyncio
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct
import logging

from ..config import QDRANT_CONFIG

logger = logging.getLogger(__name__)

class QdrantService:
    """Qdrant vector database service"""
    
    def __init__(self):
        self.client = None
        self.collections = {
            "company_offerings": "dextrends_offerings",
            "faq": "dextrends_faq"
        }
        
    async def connect(self):
        """Initialize Qdrant client connection"""
        try:
            self.client = QdrantClient(
                url=QDRANT_CONFIG["url"],
                api_key=QDRANT_CONFIG["api_key"]
            )
            
            # Verify connection
            collections = await asyncio.to_thread(self.client.get_collections)
            logger.info(f"Connected to Qdrant. Existing collections: {[c.name for c in collections.collections]}")
            
            # Initialize collections
            await self._initialize_collections()
            
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise
    
    async def _initialize_collections(self):
        """Initialize required collections with proper configuration"""
        for collection_key, collection_name in self.collections.items():
            try:
                # Check if collection exists
                try:
                    await asyncio.to_thread(
                        self.client.get_collection,
                        collection_name=collection_name
                    )
                    exists = True
                except Exception:
                    exists = False
                
                if not exists:
                    # Create collection with OpenAI embedding dimensions (1536 for text-embedding-ada-002)
                    await asyncio.to_thread(
                        self.client.create_collection,
                        collection_name=collection_name,
                        vectors_config=VectorParams(
                            size=1536,  # OpenAI embedding dimension
                            distance=Distance.COSINE
                        )
                    )
                    logger.info(f"Created collection: {collection_name}")
                else:
                    logger.info(f"Collection already exists: {collection_name}")
                    
            except Exception as e:
                logger.error(f"Failed to initialize collection {collection_name}: {e}")
                raise
    
    async def add_points(self, collection_key: str, points: List[Dict[str, Any]]) -> bool:
        """Add points to a collection"""
        try:
            collection_name = self.collections[collection_key]
            
            # Convert points to Qdrant format
            qdrant_points = []
            for point in points:
                qdrant_points.append(
                    PointStruct(
                        id=point["id"],
                        vector=point["vector"],
                        payload=point["payload"]
                    )
                )
            
            # Upsert points (insert or update)
            await asyncio.to_thread(
                self.client.upsert,
                collection_name=collection_name,
                points=qdrant_points
            )
            
            logger.info(f"Added {len(qdrant_points)} points to {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add points to collection {collection_key}: {e}")
            return False
    
    async def search(
        self, 
        collection_key: str, 
        query_vector: List[float], 
        limit: int = 5,
        score_threshold: float = 0.7,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors in a collection"""
        try:
            collection_name = self.collections[collection_key]
            
            # Build filter if provided
            query_filter = None
            if filter_conditions:
                query_filter = models.Filter(
                    must=[
                        models.FieldCondition(
                            key=key,
                            match=models.MatchValue(value=value)
                        ) for key, value in filter_conditions.items()
                    ]
                )
            
            # Perform search
            search_result = await asyncio.to_thread(
                self.client.search,
                collection_name=collection_name,
                query_vector=query_vector,
                query_filter=query_filter,
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True,
                with_vectors=False
            )
            
            # Format results
            results = []
            for scored_point in search_result:
                results.append({
                    "id": scored_point.id,
                    "score": scored_point.score,
                    "payload": scored_point.payload
                })
            
            logger.info(f"Found {len(results)} results in {collection_name}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to search in collection {collection_key}: {e}")
            return []
    
    async def delete_points(self, collection_key: str, point_ids: List[str]) -> bool:
        """Delete points from a collection"""
        try:
            collection_name = self.collections[collection_key]
            
            await asyncio.to_thread(
                self.client.delete,
                collection_name=collection_name,
                points_selector=models.PointIdsList(
                    points=point_ids
                )
            )
            
            logger.info(f"Deleted {len(point_ids)} points from {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete points from collection {collection_key}: {e}")
            return False
    
    async def get_collection_info(self, collection_key: str) -> Dict[str, Any]:
        """Get information about a collection"""
        try:
            collection_name = self.collections[collection_key]
            
            info = await asyncio.to_thread(
                self.client.get_collection,
                collection_name=collection_name
            )
            
            return {
                "name": collection_name,
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "points_count": info.points_count,
                "segments_count": info.segments_count,
                "status": info.status
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection info for {collection_key}: {e}")
            return {}
    
    async def health_check(self) -> bool:
        """Check if Qdrant service is healthy"""
        try:
            if not self.client:
                return False
                
            # Try to get collections list
            await asyncio.to_thread(self.client.get_collections)
            return True
            
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from Qdrant"""
        try:
            if self.client:
                await asyncio.to_thread(self.client.close)
                self.client = None
            logger.info("Disconnected from Qdrant")
        except Exception as e:
            logger.error(f"Error disconnecting from Qdrant: {e}")


# Global Qdrant service instance
qdrant_service = QdrantService()

async def get_qdrant_client() -> QdrantService:
    """Get the global Qdrant service instance"""
    if not qdrant_service.client:
        await qdrant_service.connect()
    return qdrant_service