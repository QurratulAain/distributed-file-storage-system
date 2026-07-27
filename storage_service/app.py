"""
Storage Service
---------------
This microservice has exactly ONE job: store file bytes and return them
when asked. It knows nothing about users, metadata, or the frontend.
That single responsibility is what makes it a legitimate, independent
component of the distributed system rather than a folder living inside
the backend.

Endpoints:
    GET  /health              -> confirms the service is alive
    POST /upload               -> accepts a file, saves it, returns its stored name
    GET  /download/<filename>  -> returns the raw file bytes
    GET  /files                -> lists what is currently stored (debug/demo use)
"""

import os
import uuid
from flask import Flask, request, send_from_directory, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Where files actually live on disk. In the deployed version, this becomes
# a persistent disk/volume on whichever host you pick (Render/Railway/etc).
STORAGE_DIR = os.path.join(os.path.dirname(__file__), "storage")
os.makedirs(STORAGE_DIR, exist_ok=True)

# Keep the demo safe and predictable: cap upload size (10 MB here).
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "storage_service"}), 200


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "no file part in request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "empty filename"}), 400

    original_name = secure_filename(file.filename)

    # Prefix with a UUID so two users uploading "resume.pdf" never collide.
    stored_name = f"{uuid.uuid4().hex}_{original_name}"
    save_path = os.path.join(STORAGE_DIR, stored_name)
    file.save(save_path)

    size_bytes = os.path.getsize(save_path)

    return jsonify({
        "stored_name": stored_name,
        "original_name": original_name,
        "size_bytes": size_bytes,
    }), 201


@app.route("/download/<path:stored_name>", methods=["GET"])
def download(stored_name):
    safe_name = secure_filename(stored_name)
    if not os.path.exists(os.path.join(STORAGE_DIR, safe_name)):
        return jsonify({"error": "file not found"}), 404
    return send_from_directory(STORAGE_DIR, safe_name, as_attachment=True)


@app.route("/files", methods=["GET"])
def list_files():
    files = os.listdir(STORAGE_DIR)
    return jsonify({"files": files}), 200


if __name__ == "__main__":
    # Runs on port 5001 so it doesn't clash with the backend (port 5000).
    app.run(host="0.0.0.0", port=5001, debug=True)