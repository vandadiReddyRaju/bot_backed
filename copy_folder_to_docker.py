# copy_folder_to_docker.py

import os
import pandas as pd
from zipfile import ZipFile, BadZipFile
import subprocess
import shutil
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_docker_available():
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def get_question_details(question_id, column_name):
    csv_file_path = 'commands.csv' 
    
    try:
        df = pd.read_csv(csv_file_path)
        if column_name not in df.columns:
            print(f"Column '{column_name}' not found in the CSV.")
            return None
            
        # Clean the data
        df['question_command_id'] = df['question_command_id'].str.strip()
        
        # Try both question_id and question_command_id columns
        if 'question_command_id' in df.columns:
            result = df[df['question_command_id'] == question_id]
        else:
            result = df[df['question_id'] == question_id]
        
        if result.empty:
            print(f"Question ID '{question_id}' not found in the CSV.")
            return None
            
        return str(result[column_name].iloc[0])
    
    except FileNotFoundError:
        print(f"CSV file '{csv_file_path}' not found in directory: {os.getcwd()}")
        return None
    except pd.errors.EmptyDataError:
        print("The CSV file is empty.")
        return None
    except Exception as e:
        print(f"An error occurred while reading CSV: {e}")
        return None

def check_and_delete_folder(folder_path):
    if os.path.isdir(folder_path):
        try:
            shutil.rmtree(folder_path)
            print(f"Folder '{folder_path}' has been deleted.")
            return True
        except Exception as e:
            print(f"Error occurred while deleting the folder: {e}")
            return False
    return True  # Return True if folder doesn't exist, as that's what we want

def extract_zip(zip_path, output_folder="./workspace"):
    try:
        # Create output folder if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)
        
        with ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(output_folder)
        print(f"Extracted '{zip_path}' to '{output_folder}'.")
        return output_folder
    except BadZipFile:
        print("The provided file is not a valid ZIP.")
        return None
    except Exception as e:
        print(f"An error occurred while extracting ZIP: {e}")
        return None

def copy_folder_to_docker(container_id, input_folder, output_folder):
    try:
        if not check_docker_available():
            raise Exception("Docker is not installed or not accessible. Please ensure Docker is properly installed and running.")

        if not os.path.exists(input_folder):
            raise ValueError(f"Input folder '{input_folder}' does not exist")
        
        print(f"output_folder : {output_folder}")
        
        # Check if container exists and is running
        check_container = subprocess.run(f"docker container inspect {container_id}", 
                                      shell=True, capture_output=True, text=True)
        if check_container.returncode != 0:
            raise Exception(f"Container '{container_id}' does not exist or is not accessible")
        
        # Try creating directory with root user
        mkdir_cmd = f"docker exec --user root {container_id} mkdir -p {output_folder}"
        result = subprocess.run(mkdir_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Warning: mkdir command failed: {result.stderr}")
            # Try alternative approach
            alt_cmd = f"docker exec {container_id} sh -c 'mkdir -p {output_folder}'"
            alt_result = subprocess.run(alt_cmd, shell=True, capture_output=True, text=True)
            if alt_result.returncode != 0:
                raise Exception(f"Failed to create directory: {alt_result.stderr}")
        
        # Set permissions on the directory
        chmod_cmd = f"docker exec --user root {container_id} chmod -R 777 {output_folder}"
        chmod_result = subprocess.run(chmod_cmd, shell=True, capture_output=True, text=True)
        if chmod_result.returncode != 0:
            print(f"Warning: chmod command failed: {chmod_result.stderr}")
        
        # Copy files to Docker container
        copy_cmd = f"docker cp {input_folder}/. {container_id}:{output_folder}"
        copy_result = subprocess.run(copy_cmd, shell=True, capture_output=True, text=True)
        
        if copy_result.returncode != 0:
            raise Exception(f"Copy failed: {copy_result.stderr}")
            
        print(f"Contents of '{input_folder}' have been copied to '{output_folder}' in container '{container_id}'")
        
    except Exception as e:
        print(f"Error in copy_folder_to_docker: {str(e)}")
        raise

def prepare_docker_environment(question_id, zip_path, container_id):
    try:
        # Check Docker availability first
        if not check_docker_available():
            print("Docker is not installed or not accessible. Please ensure Docker is properly installed and running.")
            return
            
        # Get folder location from CSV
        folder = get_question_details(question_id, "question_folder_location")
        if not folder:
            print(f"Could not find folder location for question ID: {question_id}")
            return
        
        print(f"Found folder location: {folder}")
        
        # Clean workspace
        if check_and_delete_folder("./workspace"):
            print("Workspace cleaned.")
        else:
            print("Workspace could not be cleaned.")
            return
        
        # Extract code from ZIP
        output_folder = extract_zip(zip_path)
        if not output_folder:
            print("Failed to extract ZIP. Aborting Docker preparation.")
            return
        
        # Copy to Docker
        try:
            copy_folder_to_docker(container_id, output_folder, folder)
            print("Docker environment prepared successfully")
        except Exception as e:
            print(f"Failed to copy folder to Docker: {e}")
            return
        
    except Exception as e:
        print(f"Error in prepare_docker_environment: {str(e)}")
        raise
