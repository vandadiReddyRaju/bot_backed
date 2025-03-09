from flask import Flask, request, jsonify
from flask_cors import CORS
from helpers import llm_call, llm_call_with_image
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure workspace paths
WORKSPACE_ROOT = os.getenv('WORKSPACE_ROOT', '/home/workspace')
DOCKER_WORKSPACE = os.getenv('DOCKER_WORKSPACE', '/home/workspace')

@app.route('/run-api', methods=['POST'])
def run_api():
    data = request.get_json()

    system_prompt = data.get("system_prompt")
    user_prompt = data.get("user_prompt")
    images = data.get("images", [])

    # Ensure workspace directories exist
    os.makedirs(WORKSPACE_ROOT, exist_ok=True)
    if not os.path.exists(DOCKER_WORKSPACE):
        os.makedirs(DOCKER_WORKSPACE, exist_ok=True)

    try:
        # Choose the correct function based on your inputs
        if images:
            result = llm_call_with_image(system_prompt, user_prompt, images)
        else:
            result = llm_call(system_prompt, user_prompt)
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Use environment variables for host and port
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    app.run(host=host, port=port, debug=False)