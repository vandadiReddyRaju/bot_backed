from flask import Flask, request, jsonify
from flask_cors import CORS
from helpers import llm_call, llm_call_with_image
import os
from dotenv import load_dotenv
import tempfile
from werkzeug.utils import secure_filename

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure workspace paths
WORKSPACE_ROOT = os.getenv('WORKSPACE_ROOT', '/home/workspace')
DOCKER_WORKSPACE = os.getenv('DOCKER_WORKSPACE', '/home/workspace')

# Configure upload settings
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB limit
ALLOWED_EXTENSIONS = {'zip'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
        app.logger.error(f"Error in run-api: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/process', methods=['POST'])
def process_file():
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

        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            filename = secure_filename(file.filename)
            filepath = os.path.join(temp_dir, filename)
            file.save(filepath)
            
            # Process the file here
            # Your existing processing logic goes here
            
            return jsonify({"response": "File processed successfully"})
            
    except Exception as e:
        app.logger.error(f"Error processing file: {str(e)}")
        return jsonify({"error": str(e)}), 500

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
    # Use environment variables for host and port
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    
    # Configure max content length
    app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
    
    # Run in production mode
    app.run(host=host, port=port, debug=False)