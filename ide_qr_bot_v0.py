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
        if not self.folder_location:
            return "Error: Could not find question details for the given question ID"
            
        try:
            self.query_category = self.query_router.classify_query().strip()
            if self.query_category == "other":
                return "<mentor_required>"
                
            logger.info(f"Query Category: {self.query_category}")
            check_and_delete_folder("./workspace")
            
            # Extract and prepare Docker environment
            if self.zip_path:
                try:
                    copy_folder_to_docker(self.container_id, self.zip_path, self.folder_location)
                    self.repo_state = extract_file_contents_with_tree("./workspace", full_desc=True)
                except Exception as e:
                    logger.error(f"Error setting up Docker environment: {e}")
                    return "Error: Unable to set up the development environment. Please try again later."
            
            return self._generate_bot_response_based_on_category()
            
        except Exception as e:
            logger.error(f"Error in get_bot_response: {e}")
            return "Error: Something went wrong while processing your request. Please try again later."
    
    def _generate_bot_response_based_on_category(self):
        try:
            if "Test case failures" in self.query_category or \
               "Unexpected output" in self.query_category or \
               "Mistakes Explanation" in self.query_category:
                
                if not self.zip_path:
                    return "<please_attach_code_response>"
                
                # Prepare issue context with question details
                test_cases = self.question_test_cases
                context = {
                    "user_query": self.query_router.updated_query_context,
                    "student_code": self.repo_state,
                    "test_cases": test_cases,
                    "question_content": self.question_content
                }
                issue_context = f"""
                User Query: {context['user_query']}
                Question: {context['question_content']}
                Student Code: {context['student_code']}
                Test Cases: {context['test_cases']}
                """
                logger.info("Sending test case analysis request to LLM")
                return llm_call(get_test_cases_qr_v0_prompt(), issue_context)

            elif "Fix specific errors" in self.query_category:
                if not self.zip_path:
                    return "<please_attach_code_response>"
                    
                issue_context = f"""
                Question: {self.question_content}
                Student Code: {self.repo_state}
                Issue: {self.query_router.updated_query_context}
                """
                logger.info("Sending error analysis request to LLM")
                return llm_call(get_specific_errors_qr_v0_prompt(), issue_context)

            elif "Code publishing issue" in self.query_category:
                logger.info("Sending publishing issue request to LLM")
                return llm_call(get_publishing_related_query_system_prompt(),
                              f"User Query: {self.query_router.updated_query_context}")

            elif "IDE related issue" in self.query_category:
                logger.info("Sending IDE issue request to LLM")
                return llm_call(get_ide_related_queries_system_prompt(),
                              f"User Query: {self.query_router.updated_query_context}")

            else:
                logger.warning(f"Unhandled query category: {self.query_category}")
                return "<mentor_required>"

        except Exception as e:
            logger.error(f"Error generating bot response: {e}")
            return "Error: Unable to generate response. Please try again later."
