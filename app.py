from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import logging
from ide_qr_bot_v0 import QRBot
from helpers import check_and_delete_folder
import tempfile
import shutil
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": ["https://ide-mentor-bot-frontend.onrender.com"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure upload settings
UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'uploads')
ALLOWED_EXTENSIONS = {'zip'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

@app.route('/')
def home():
    """Health check endpoint."""
    return jsonify({"status": "ok"}), 200

@app.route('/process', methods=['POST'])
def process_file():
    """Process uploaded file and generate response."""
    try:
        logger.info("Received file upload request")
        logger.info(f"Files in request: {list(request.files.keys())}")
        logger.info(f"Form data: {list(request.form.keys())}")
        
        if 'zip' not in request.files:
            logger.error("No file part in request")
            return jsonify({"error": "No file uploaded"}), 400
            
        file = request.files['zip']
        query = request.form.get('query', '')
        
        logger.info(f"File received: {file.filename}")
        logger.info(f"Query received: {query}")
        
        if not file or file.filename == '':
            logger.error("No file selected")
            return jsonify({"error": "No file selected"}), 400
            
        if not allowed_file(file.filename):
            logger.error(f"Invalid file type: {file.filename}")
            return jsonify({"error": "Invalid file type"}), 400

        # Create temp directory for file processing
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, secure_filename(file.filename))
        
        try:
            # Save and process the file
            file.save(zip_path)
            logger.info(f"File saved to: {zip_path}")
            
            # Extract question ID from filename
            question_id = get_question_id_from_filename(file.filename)
            if not question_id:
                logger.error("Invalid question ID")
                return jsonify({"error": "Invalid question ID"}), 400

            # Initialize QR Bot
            qr_bot = QRBot(query, question_id, zip_path=zip_path)
            
            # Get bot response
            response = qr_bot.get_bot_response()
            logger.info(response)
            if not response:
                logger.error("Failed to get response from LLM")
                return jsonify({"error": "Failed to get response from LLM"}), 500
                
            logger.info("Successfully generated response")
            return jsonify({"response": response})

        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            return jsonify({"error": str(e)}), 500
            
        finally:
            # Clean up temp directory
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    logger.info("Cleaned up temp directory")
            except Exception as e:
                logger.warning(f"Error cleaning up temp directory: {str(e)}")

    except Exception as e:
        logger.error(f"Error in process_file: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.after_request
def after_request(response):
    """Add CORS headers to all responses."""
    response.headers.add('Access-Control-Allow-Origin', 'https://ide-mentor-bot-frontend.onrender.com')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Error handlers
@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file size exceeding limit."""
    return jsonify({"error": "File size exceeds 50MB limit"}), 413

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"error": "Resource not found"}), 404

if __name__ == '__main__':
    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    # Run the app
    app.run(host='0.0.0.0', port=10000)
