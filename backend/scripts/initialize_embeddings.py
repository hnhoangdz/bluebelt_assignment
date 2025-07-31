"""
Script to initialize embeddings and vector database for Dextrends AI Chatbot
"""

import asyncio
import logging
import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.embedding_service import get_embedding_service
from core.qdrant_client import get_qdrant_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def initialize_vector_database():
    """Initialize vector database with company data"""
    try:
        logger.info("Starting vector database initialization...")
        
        # Get services
        embedding_service = await get_embedding_service()
        qdrant_client = await get_qdrant_client()
        
        # Check Qdrant connection
        if not await qdrant_client.health_check():
            logger.error("Qdrant health check failed. Please ensure Qdrant is running.")
            return False
        
        logger.info("Qdrant connection verified")
        
        # Initialize embeddings
        success = await embedding_service.initialize_embeddings(force_refresh=False)
        
        if success:
            logger.info("✅ Vector database initialization completed successfully!")
            
            # Print collection info
            offerings_info = await qdrant_client.get_collection_info("company_offerings")
            faq_info = await qdrant_client.get_collection_info("faq")
            
            logger.info(f"Company Offerings Collection: {offerings_info.get('points_count', 0)} points")
            logger.info(f"FAQ Collection: {faq_info.get('points_count', 0)} points")
            
            return True
        else:
            logger.error("❌ Vector database initialization failed")
            return False
            
    except Exception as e:
        logger.error(f"Error during initialization: {e}")
        return False

async def main():
    """Main initialization function"""
    logger.info("Dextrends AI Chatbot - Vector Database Initialization")
    logger.info("=" * 60)
    
    success = await initialize_vector_database()
    
    if success:
        logger.info("🎉 Initialization completed successfully!")
        logger.info("Your Dextrends AI Chatbot is ready to use.")
    else:
        logger.error("💥 Initialization failed!")
        logger.error("Please check the logs above for error details.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())