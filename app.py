from flask import Flask, request, jsonify
from flask_cors import CORS
from helpers import llm_call, llm_call_with_image, extract_file_contents_with_tree
import os
from dotenv import load_dotenv
import tempfile
from werkzeug.utils import secure_filename
import logging
import zipfile
import shutil
from ide_qr_bot_v0 import QRBot  # Add QRBot import

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # Enable CORS for all routes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure workspace paths
WORKSPACE_ROOT = os.getenv('WORKSPACE_ROOT', '/home/workspace')
DOCKER_WORKSPACE = os.getenv('DOCKER_WORKSPACE', '/home/workspace')

# Configure upload settings
UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'uploads')
ALLOWED_EXTENSIONS = {'zip'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_zip(zip_path, extract_path):
    """Extract zip file to the specified path."""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        return True
    except Exception as e:
        logger.error(f"Error extracting zip file: {str(e)}")
        return False

def get_question_id_from_filename(filename):
    """Extract question ID from filename."""
    try:
        # Remove .zip extension if present
        question_id = filename.replace('.zip', '')
        logger.info(f"Extracted question ID: {question_id}")
        return question_id
    except Exception as e:
        logger.error(f"Error extracting question ID from filename: {str(e)}")
        return None

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "message": "API is running"}), 200

@app.route('/run-api', methods=['POST'])
def run_api():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        system_prompt = data.get("system_prompt")
        user_prompt = data.get("user_prompt")
        images = data.get("images", [])

        if not system_prompt or not user_prompt:
            return jsonify({"error": "Missing required fields"}), 400

        # Ensure workspace directories exist
        os.makedirs(WORKSPACE_ROOT, exist_ok=True)
        if not os.path.exists(DOCKER_WORKSPACE):
            os.makedirs(DOCKER_WORKSPACE, exist_ok=True)

        # Choose the correct function based on your inputs
        if images:
            result = llm_call_with_image(system_prompt, user_prompt, images)
        else:
            result = llm_call(system_prompt, user_prompt)
        
        if not result:
            return jsonify({"error": "Failed to get response from LLM"}), 500
            
        return jsonify({"result": result})
    
    except Exception as e:
        logger.error(f"Error in run-api: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/process', methods=['POST'])
def process_file():
    temp_dir = None
    extract_dir = None
    try:
        if 'zip' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['zip']
        query = request.form.get('query')
        
        if not file or not file.filename:
            return jsonify({"error": "No file selected"}), 400
            
        if not query:
            return jsonify({"error": "No query provided"}), 400
            
        if not allowed_file(file.filename):
            return jsonify({"error": "Invalid file type. Only ZIP files are allowed"}), 400

        # Create temporary directories
        temp_dir = tempfile.mkdtemp()
        extract_dir = tempfile.mkdtemp()
        
        try:
            # Save and extract the zip file
            zip_path = os.path.join(temp_dir, secure_filename(file.filename))
            file.save(zip_path)
            
            # Get question ID from filename
            question_id = get_question_id_from_filename(file.filename)
            if not question_id:
                return jsonify({"error": "Invalid file name format. Expected format: questionID_filename.zip"}), 400

            # Initialize QRBot with the query and file details
            qr_bot = QRBot(
                user_query=query,
                question_id=question_id,
                zip_path=zip_path
            )
            
            # Get bot response using the QRBot system
            result = qr_bot.get_bot_response()
            
            if not result or result == "<mentor_required>":
                # Fallback to generic analysis if QRBot can't handle the query
                logger.info("Falling back to generic code analysis")
                if not extract_zip(zip_path, extract_dir):
                    return jsonify({"error": "Failed to extract zip file"}), 500
                
                file_contents = extract_file_contents_with_tree(extract_dir, full_desc=True)
                system_prompt = """You are an expert code reviewer and mentor. Analyze the provided code and respond to the user's query.
                Focus on best practices, potential issues, and improvements. If there are any errors, explain them clearly and provide solutions."""
                
                full_prompt = f"Query: {query}\n\nCode Analysis:\n{file_contents}"
                result = llm_call(system_prompt, full_prompt)
            
            if not result:
                return jsonify({"error": "Failed to get response from LLM"}), 500
            
            return jsonify({"response": result})
            
        except Exception as e:
            logger.error(f"Error processing file contents: {str(e)}")
            return jsonify({"error": f"Error processing file: {str(e)}"}), 500
            
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        return jsonify({"error": str(e)}), 500
        
    finally:
        # Clean up temporary directories
        try:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            if extract_dir and os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)
        except Exception as e:
            logger.warning(f"Error cleaning up temporary directories: {str(e)}")

@app.after_request
def after_request(response):
    """Add CORS headers to all responses."""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Error handlers
@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "File too large. Maximum size is 50MB"}), 413

@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": "Resource not found"}), 404

if __name__ == '__main__':
    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    # Use environment variables for host and port
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    
    # Run in production mode
    app.run(host=host, port=port, debug=False)