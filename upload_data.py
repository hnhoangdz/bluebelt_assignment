#!/usr/bin/env python3
"""
Script to upload company offerings and FAQ data to Qdrant collections
"""

import asyncio
import json
import logging
import sys
import os
from pathlib import Path

# Change to the project directory and add backend to path
project_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(project_dir)
sys.path.insert(0, project_dir)
sys.path.insert(0, os.path.join(project_dir, 'backend'))

from backend.services.embedding_service import EmbeddingService
from backend.core.qdrant_client import get_qdrant_client

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataUploader:
    def __init__(self):
        self.embedding_service = EmbeddingService()
    
    async def upload_company_offerings(self, offerings_file: str) -> bool:
        """Upload company offerings to 'dextrends_offerings' collection"""
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
            
            company_embedding = await self.embedding_service.generate_embedding(company_text.strip())
            points.append({
                "id": self.embedding_service._generate_point_id(company_text, "company_info"),
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
                service_embedding = await self.embedding_service.generate_embedding(service_text.strip())
                
                # Create point
                points.append({
                    "id": self.embedding_service._generate_point_id(service_text, f"service_{service.get('id', '')}"),
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
            
            # Store embeddings in Qdrant using the collection key
            success = await qdrant_client.add_points("company_offerings", points)
            
            if success:
                logger.info(f"Successfully uploaded {len(points)} company offering points to 'dextrends_offerings'")
                return True
            else:
                logger.error("Failed to store company offering embeddings")
                return False
                
        except Exception as e:
            logger.error(f"Failed to upload company offerings: {e}")
            return False
    
    async def upload_faq_data(self, faq_file: str) -> bool:
        """Upload FAQ data to 'dextrends_faq' collection"""
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
                faq_embedding = await self.embedding_service.generate_embedding(faq_text.strip())
                
                # Create point
                points.append({
                    "id": self.embedding_service._generate_point_id(faq_text, f"faq_{faq.get('id', '')}"),
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
            
            # Store embeddings in Qdrant using the collection key
            success = await qdrant_client.add_points("faq", points)
            
            if success:
                logger.info(f"Successfully uploaded {len(points)} FAQ points to 'dextrends_faq'")
                return True
            else:
                logger.error("Failed to store FAQ embeddings")
                return False
                
        except Exception as e:
            logger.error(f"Failed to upload FAQ data: {e}")
            return False

async def main():
    """Main upload function"""
    logger.info("Starting data upload process...")
    
    uploader = DataUploader()
    
    # Upload company offerings
    logger.info("Uploading company offerings...")
    offerings_success = await uploader.upload_company_offerings(
        os.path.join(project_dir, "data", "company_offerings.json")
    )
    
    # Upload FAQ data
    logger.info("Uploading FAQ data...")
    faq_success = await uploader.upload_faq_data(
        os.path.join(project_dir, "data", "faq_data.json")
    )
    
    if offerings_success and faq_success:
        logger.info("✅ Successfully uploaded all data to Qdrant collections!")
        return True
    else:
        logger.error("❌ Failed to upload some data")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)