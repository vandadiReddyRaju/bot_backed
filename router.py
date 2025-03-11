from helpers import parse_html_to_dict
from helpers import download_image, encode_image_to_base64, llm_call_with_image
from prompts import get_query_classification_prompt
import json
import logging
import os
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QueryRouter: 
    def __init__(self, query):
        self.query = query
        self.query_text = ""
        self.query_imgs = []
        self.updated_query_context = ""
        self.temp_dir = None
    
    def parse_query(self):
        """Parse HTML query and extract text and images."""
        try:
            # If query is not HTML, treat it as plain text
            if not self.query.strip().startswith('<'):
                self.query_text = self.query.strip()
                logger.info(f"Processing plain text query: {self.query_text}")
                return
                
            text, imgs = parse_html_to_dict(self.query)
            image_strings = []
            
            if imgs:
                self.temp_dir = tempfile.mkdtemp()
                
            for img in imgs:
                try:
                    image_path = download_image(img, save_dir=self.temp_dir)
                    if image_path:
                        image_base64, image_format = encode_image_to_base64(image_path)
                        image_strings.append({
                            "extension": image_format,
                            "content": image_base64
                        })
                except Exception as e:
                    logger.error(f"Error processing image {img}: {str(e)}")
                    continue
                    
            self.query_text = text.strip()
            self.query_imgs = image_strings
            logger.info(f"Successfully parsed query with {len(image_strings)} images")
            
        except Exception as e:
            logger.error(f"Error parsing query: {str(e)}")
            # Fallback to treating query as plain text
            self.query_text = self.query.strip()
            self.query_imgs = []
        finally:
            if self.temp_dir and os.path.exists(self.temp_dir):
                try:
                    import shutil
                    shutil.rmtree(self.temp_dir)
                except Exception as e:
                    logger.warning(f"Error cleaning up temp directory: {str(e)}")

    def classify_query(self):
        """Classify the query using LLM and update context."""
        try:
            self.parse_query()
            
            if not self.query_text:
                self.query_text = "Please provide your question or describe the issue you're facing."
                
            result = llm_call_with_image(
                get_query_classification_prompt(),
                self.query_text,
                self.query_imgs
            )
            
            if not result:
                return "other"
                
            try:
                res_json = json.loads(result.replace("```json", "").replace("```", ""))
                query_category = res_json.get('query_category', 'other').strip()
                return query_category
            except:
                return "other"
            
        except Exception as e:
            logger.error(f"Error classifying query: {str(e)}")
            return "other"

if __name__ == "__main__": 
    # Test code commented out for production
    pass