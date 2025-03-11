import base64
from io import BytesIO
from PIL import Image
from bs4 import BeautifulSoup
import requests
import os
import logging
from zipfile import ZipFile, BadZipFile
import subprocess
import re
import shutil
import pandas as pd
import glob
import time
from dotenv import load_dotenv
from openai import OpenAI
import openai
import tempfile
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def get_api_key():
    """Safely retrieve API key from environment variables."""
    api_key = os.getenv("api_key")
    if not api_key:
        logger.error("API key not found in environment variables")
        raise ValueError("API key not configured")
    return api_key

def parse_html_to_dict(html_text):
    """Parse HTML content to extract text and image links."""
    try:
        soup = BeautifulSoup(html_text, 'html.parser')
        text_parts = []
        for p in soup.find_all('p'):
            text_parts.append(p.get_text(strip=True))
        combined_text = " ".join(text_parts)
        img_links = [img['src'] for img in soup.find_all('img')]

        return combined_text, img_links
    except Exception as e:
        logger.error(f"Error parsing HTML: {str(e)}")
        raise

def llm_call(system_prompt, user_prompt):
    """Make an API call to the LLM service."""
    try:
        logger.info("Calling OpenRouter API...")
        
        api_key = get_api_key()
        
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            timeout=60
        )
                    
        completion = client.chat.completions.create(
            model="deepseek/deepseek-r1-zero:free",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
        )
        result = completion.choices[0].message.content
        logger.info("Successfully received response from OpenRouter")
        return result

    except openai.APITimeoutError as e:
        logger.error(f"API timeout error: {str(e)}")
        return "Error: Request timed out. Please try again."
    except openai.APIConnectionError as e:
        logger.error(f"API connection error: {str(e)}")
        return "Error: Failed to connect to the API. Please check your internet connection."
    except openai.APIError as e:
        logger.error(f"OpenRouter API error: {str(e)}")
        return "Error: An error occurred while processing your request. Please try again."
    except Exception as e:
        logger.error(f"Error calling OpenRouter API: {str(e)}")
        return f"Error: {str(e)}"

def llm_call_with_image(system_prompt, user_prompt_text, user_base_64_imgs):
    """Make an API call to the LLM service with image content."""
    try:
        logger.info("Calling OpenRouter API with images...")
        
        api_key = get_api_key()

        # Prepare the messages with images
        user_prompt_content = [{"type": "text", "text": user_prompt_text}]
        for img in user_base_64_imgs:
            img_content = {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/{img['extension']};base64,{img['content']}"
                }
            }
            user_prompt_content.append(img_content)
            
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            timeout=60
        )
                    
        completion = client.chat.completions.create(
            model="deepseek/deepseek-r1-zero:free",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt_content}
            ],
        )
        
        result = completion.choices[0].message.content
        logger.info("Successfully received response from OpenRouter")
        return result
        
    except openai.APITimeoutError as e:
        logger.error(f"API timeout error: {str(e)}")
        return "Error: Request timed out. Please try again."
    except openai.APIConnectionError as e:
        logger.error(f"API connection error: {str(e)}")
        return "Error: Failed to connect to the API. Please check your internet connection."
    except openai.APIError as e:
        logger.error(f"OpenRouter API error: {str(e)}")
        return "Error: An error occurred while processing your request. Please try again."
    except Exception as e:
        logger.error(f"Error calling OpenRouter API with images: {str(e)}")
        return f"Error: {str(e)}"

def download_image(url):
    """Download an image from a URL and save it temporarily."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(url).suffix) as temp_file:
            temp_file.write(response.content)
            return temp_file.name
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download image from {url}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error processing image from {url}: {str(e)}")
        raise

def encode_image_to_base64(image_path):
    """Encode an image file to base64 string."""
    try:
        with Image.open(image_path) as image:
            image_format = image.format.lower()
            buffered = BytesIO()
            image.save(buffered, format=image_format.upper())
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
        # Clean up the temporary file
        try:
            os.unlink(image_path)
        except Exception as e:
            logger.warning(f"Failed to delete temporary image file {image_path}: {str(e)}")
            
        return img_str, image_format
        
    except Exception as e:
        logger.error(f"Error encoding image {image_path}: {str(e)}")
        raise

def extract_file_contents_with_tree(folder_path, full_desc=False):
    """Extract contents of files in a directory tree."""
    try:
        result = []
        tree = []
        allowed_extensions = ('.json', '.js', '.ts', '.html', '.css')

        def add_to_tree(path, indent=""):
            parts = path.split(os.sep)
            tree.append(f"{indent}* {parts[-1]}")

        for root, dirs, files in os.walk(folder_path):
            if 'node_modules' in dirs:
                dirs.remove('node_modules')

            level = root.replace(folder_path, '').count(os.sep)
            indent = '  ' * level
            add_to_tree(root, indent)

            for file in files:
                if file.endswith(allowed_extensions):
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, folder_path)
                    
                    add_to_tree(file, indent + '  ')
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        result.append(f"\n{relative_path}:\n{content}\n")
                    except Exception as e:
                        logger.error(f"Error reading file {relative_path}: {str(e)}")
                        result.append(f"\nError reading file {relative_path}: {str(e)}\n")

        tree_str = "\n".join(tree)
        content_str = "".join(result)

        final_output = f"Directory Tree: \n{tree_str}"
        if full_desc:
            final_output += f"\n\nFile contents: \n{content_str}"
        
        return final_output
        
    except Exception as e:
        logger.error(f"Error extracting file contents: {str(e)}")
        raise

def get_question_details_from_zip(zip_filename):
    """
    Retrieves multiple details for a question based on the zip filename.

    Args:
        zip_filename (str): The name of the zip file without the '.zip' extension.

    Returns:
        dict: A dictionary containing 'question_command_id', 'question_content', and 'question_test_cases'.
              Returns None if no matching record is found.
    """
    csv_file_path = 'commands.csv' 
    
    try:
        # Read CSV with explicit encoding and handling for special characters
        df = pd.read_csv(csv_file_path, encoding='utf-8', on_bad_lines='skip')
        
        # Clean the data
        df['question_command_id'] = df['question_command_id'].str.strip()
        
        # Print debug information
        print("CSV File Info:")
        print(f"Total rows: {len(df)}")
        print(f"Columns: {df.columns.tolist()}")
        print(f"First few question IDs: {df['question_command_id'].head().tolist()}")
        print(f"Looking for ID: {zip_filename}")
        
        # Update required_columns to map to existing columns
        required_columns = ['question_command_id', 'question_content', 'question_test_cases']
        for column in required_columns:
            if column not in df.columns:
                print(f"Error: Column '{column}' not found in the CSV. Available columns: {df.columns.tolist()}")
                return None
        
        # Assuming zip_filename corresponds to 'question_command_id'
        result = df[df['question_command_id'].str.contains(zip_filename, na=False, case=False)]
        
        if result.empty:
            print(f"Error: Question ID '{zip_filename}' not found in the CSV.")
            print("Available IDs:")
            for id in df['question_command_id'].unique():
                print(f"- {id}")
            return None
        
        # Assuming 'question_command_id' is unique, take the first matching row
        row = result.iloc[0]
        return {
            'question_command_id': str(row['question_command_id']).strip(),
            'question_content': str(row['question_content']),
            'question_test_cases': str(row['question_test_cases'])
        }
    
    except FileNotFoundError:
        print(f"Error: CSV file '{csv_file_path}' not found in current directory: {os.getcwd()}")
        return None
    except pd.errors.EmptyDataError:
        print("Error: The CSV file is empty")
        return None
    except Exception as e:
        logger.error(f"Error processing CSV file: {str(e)}")
        print(f"Current working directory: {os.getcwd()}")
        return None

def copy_folder_to_docker(container_id, zip_path, output_folder):
    """
    Extracts the zip file to a workspace and copies its contents to the specified Docker container folder.

    Args:
        container_id (str): The Docker container ID.
        zip_path (str): Path to the zip file.
        output_folder (str): Destination folder path inside the Docker container.

    Returns:
        None
    """
    # Ensure the zip file exists
    if not os.path.isfile(zip_path):
        raise FileNotFoundError(f"Zip file '{zip_path}' does not exist.")


    # Define workspace directory
    workspace_dir = "./workspace"


    # Clean workspace
    check_and_delete_folder(workspace_dir)


    # Extract zip to workspace
    try:
        with ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(workspace_dir)
        print(f"Extracted '{zip_path}' to '{workspace_dir}'.")
    except BadZipFile:
        print(f"The file '{zip_path}' is not a valid zip file.")
        return
    except Exception as e:
        logger.error(f"An error occurred while extracting zip: {e}")
        return


    # Create output directory inside Docker container
    create_output_cmd = f"docker exec {container_id} mkdir -p {output_folder}"
    subprocess.run(create_output_cmd, shell=True, check=True)


    # Copy contents to Docker container
    copy_cmd = f"docker cp {workspace_dir}/. {container_id}:{output_folder}"
    subprocess.run(copy_cmd, shell=True, check=True)


    print(f"Contents of '{workspace_dir}' have been copied to '{output_folder}' in container '{container_id}'.")

def check_and_delete_folder(folder_path):
    """Safely delete a folder if it exists."""
    try:
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
            logger.info(f"Successfully deleted folder: {folder_path}")
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting folder {folder_path}: {str(e)}")
        raise
