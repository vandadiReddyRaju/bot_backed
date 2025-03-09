from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import glob
from ide_qr_bot_v0 import QRBot
from copy_folder_to_docker import prepare_docker_environment
from helpers import get_question_details_from_zip
import tempfile

app = Flask(__name__)

# Enable CORS for all routes with port 3005
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:3005", "http://127.0.0.1:3005","https://ide-mentor-bot-frontend.onrender.com"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Accept"],
        "expose_headers": ["Content-Type", "Accept"]
    }
})

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Accept')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response

@app.route('/')
def health_check():
    return jsonify({"status": "ok", "message": "Server is running"}), 200

@app.route('/process', methods=['POST', 'OPTIONS'])
def process_zip_and_query():
    if request.method == 'OPTIONS':
        return '', 204

    try:
        # Get the uploaded zip file and user query
        if 'zip' not in request.files:
            return jsonify({"error": "No zip file provided"}), 400
            
        zip_file = request.files['zip']
        if not zip_file.filename:
            return jsonify({"error": "No zip file selected"}), 400
            
        user_query = request.form.get('query', '')
        if not user_query:
            return jsonify({"error": "No query provided"}), 400
        
        # Create a temporary directory to store the uploaded file
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save the uploaded zip to a temporary location
            temp_zip_path = os.path.join(temp_dir, zip_file.filename)
            zip_file.save(temp_zip_path)
            
            # Get the filename without extension
            zip_filename = os.path.splitext(zip_file.filename)[0]
            print(f"Processing zip file with ID: {zip_filename}")
            
            # Process the zip file
            question_details = get_question_details_from_zip(zip_filename)
            if not question_details:
                return jsonify({
                    "error": f"Could not find question details for ID: {zip_filename}. Please ensure the zip filename matches a valid question ID in commands.csv"
                }), 400
            
            question_command_id = question_details['question_command_id']
            question_content = question_details['question_content']
            question_test_cases = question_details['question_test_cases']
            
            print(f"Found question details for ID {question_command_id}")
            
            try:
                container_id = "dd5790b111f4"  # **Update with your container ID or manage dynamically**
                
                # Step 1: Prepare Docker environment
                prepare_docker_environment(question_command_id, temp_zip_path, container_id)
                
                # Step 2: Initialize QRBot and get response
                qrbot = QRBot(
                    user_query=user_query,
                    question_id=question_command_id,
                    zip_path=temp_zip_path,
                    question_content=question_content,
                    question_test_cases=question_test_cases
                )
                output = qrbot.get_bot_response()
                
                return jsonify({"response": output})
            except Exception as docker_error:
                print(f"Docker-related error: {str(docker_error)}")
                return jsonify({"error": f"Error setting up environment: {str(docker_error)}"}), 500
    
    except Exception as e:
        print(f"Error processing request: {str(e)}")  # Add server-side logging
        return jsonify({"error": f"Error processing request: {str(e)}"}), 500

if __name__ == "__main__":
    print("Starting Flask server on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=True)
