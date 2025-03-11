# ide_qr_bot_v0.py

from router import QueryRouter
from helpers import llm_call, extract_file_contents_with_tree, copy_folder_to_docker, check_and_delete_folder
from prompts import (
    conceptual_doubt_prompt,
    get_implementation_guidance_prompt,
    get_test_cases_qr_v0_prompt,
    get_specific_errors_qr_v0_prompt,
    get_publishing_related_query_system_prompt,
    get_ide_related_queries_system_prompt
)
import logging
import pandas as pd
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QRBot:
    def __init__(self, user_query, question_id, zip_path="", question_content="", question_test_cases=""): 
        self.user_query = user_query
        self.question_id = question_id
        self.question_content = question_content
        self.question_test_cases = question_test_cases
        self.query_category = "other"
        self.repo_state = ""
        self.query_router = QueryRouter(query=self.user_query)
        self.zip_path = zip_path
        self.container_id = "dd5790b111f4"  # **Update or manage dynamically as needed**
        
        # Get question details from CSV
        try:
            logger.info(f"Looking up question ID: {question_id}")
            df = pd.read_csv('commands.csv')
            # Look up by question_command_id
            result = df[df['question_command_id'] == question_id]
            if not result.empty:
                self.folder_location = result['question_folder_location'].iloc[0]
                self.question_content = result['question_content'].iloc[0] if 'question_content' in result.columns else ""
                self.question_test_cases = result['test_cases'].iloc[0] if 'test_cases' in result.columns else ""
                logger.info(f"Found question details for ID: {question_id}")
                logger.info(f"Folder location: {self.folder_location}")
            else:
                # Try looking up by question_id as fallback
                result = df[df['question_id'] == question_id]
                if not result.empty:
                    self.folder_location = result['question_folder_location'].iloc[0]
                    self.question_content = result['question_content'].iloc[0] if 'question_content' in result.columns else ""
                    self.question_test_cases = result['test_cases'].iloc[0] if 'test_cases' in result.columns else ""
                    logger.info(f"Found question details using question_id: {question_id}")
                    logger.info(f"Folder location: {self.folder_location}")
                else:
                    logger.warning(f"Could not find question details for ID: {question_id}")
                    self.folder_location = None
        except Exception as e:
            logger.error(f"Error getting question details: {e}")
            self.folder_location = None

    def get_bot_response(self):
        """Get bot response based on the query category."""
        try:
            # Get query category
            self.query_category = self.query_router.classify_query()
            
            if self.question_content:
                system_prompt = f"""You are an expert code reviewer and mentor. 
                Question: {self.question_content}
                Test Cases: {self.question_test_cases}
                Category: {self.query_category}
                
                Analyze the code and provide a helpful response focusing on the specific query category."""
                
                user_prompt = f"Query: {self.user_query}"
                
                response = llm_call(system_prompt, user_prompt)
                if response:
                    return response
            
            # Fallback to generic response
            system_prompt = "You are an expert code reviewer. Analyze the code and provide a helpful response."
            user_prompt = f"Query: {self.user_query}"
            
            return llm_call(system_prompt, user_prompt)
            
        except Exception as e:
            logger.error(f"Error getting bot response: {str(e)}")
            return None
