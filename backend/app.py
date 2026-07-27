"""
Backend (Coordinator) Service
-----------------------------
This service is the only thing the frontend talks to. It does NOT store
file bytes itself — it forwards them to the storage service, and it
keeps metadata about each file in its own database.

Endpoints:
    GET  /api/health
    POST /api/upload            -> multipart file (+ optional 'owner' field)
    GET  /api/files              -> list of metadata records
    GET  /api/download/<file_id> -> streams the file back, by DB id

Environment:
    STORAGE_SERVICE_URL  Base URL of the storage service.
                         Defaults to localhost for Day 1 (both services
                         running on your own machine). This is the ONE
                         line you change on Day 3 when the storage
                         service is deployed elsewhere.
"""

import os
import requests
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

from models import db, FileRecord

app = Flask(__name__)

# In local dev this allows any origin. In production, set FRONTEND_ORIGIN
# to your deployed Vercel URL (e.g. https://your-app.vercel.app) so only
# your frontend can call this API.
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "*")
CORS(app, origins=[FRONTEND_ORIGIN] if FRONTEND_ORIGIN != "*" else "*")

BASE_DIR = os.path.dirname(__file__)
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(BASE_DIR, 'metadata.db')}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

STORAGE_SERVICE_URL = os.environ.get("STORAGE_SERVICE_URL", "http://localhost:5001")


@app.route("/api/health", methods=["GET"])
def health():
    # Also reports whether the storage service is reachable —
    # useful for proving, live in the viva, that these are two real
    # independent services talking over the network.
    storage_ok = False
    try:
        r = requests.get(f"{STORAGE_SERVICE_URL}/health", timeout=3)
        storage_ok = r.status_code == 200
    except requests.exceptions.RequestException:
        storage_ok = False

    return jsonify({
        "status": "ok",
        "service": "backend",
        "storage_service_reachable": storage_ok,
    }), 200


@app.route("/api/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "no file part in request"}), 400

    file = request.files["file"]
    owner = request.form.get("owner", "anonymous")

    if file.filename == "":
        return jsonify({"error": "empty filename"}), 400

    # Forward the file to the storage service. This is the key
    # distributed-systems moment: the backend does not save this file
    # itself, it hands it to a completely separate service over HTTP.
    try:
        files_payload = {"file": (file.filename, file.stream, file.mimetype)}
        storage_response = requests.post(
            f"{STORAGE_SERVICE_URL}/upload", files=files_payload, timeout=10
        )
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"storage service unreachable: {e}"}), 502

    if storage_response.status_code != 201:
        return jsonify({"error": "storage service rejected the file",
                         "details": storage_response.text}), 502

    storage_data = storage_response.json()

    record = FileRecord(
        original_name=storage_data["original_name"],
        stored_name=storage_data["stored_name"],
        owner=owner,
        size_bytes=storage_data["size_bytes"],
    )
    db.session.add(record)
    db.session.commit()

    return jsonify({"message": "upload successful", "file": record.to_dict()}), 201


@app.route("/api/files", methods=["GET"])
def list_files():
    records = FileRecord.query.order_by(FileRecord.upload_time.desc()).all()
    return jsonify({"files": [r.to_dict() for r in records]}), 200


@app.route("/api/download/<int:file_id>", methods=["GET"])
def download_file(file_id):
    record = FileRecord.query.get(file_id)
    if record is None:
        return jsonify({"error": "no such file record"}), 404

    try:
        storage_response = requests.get(
            f"{STORAGE_SERVICE_URL}/download/{record.stored_name}", timeout=10
        )
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"storage service unreachable: {e}"}), 502

    if storage_response.status_code != 200:
        return jsonify({"error": "storage service could not find the file"}), 502

    return Response(
        storage_response.content,
        mimetype="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{record.original_name}"'
        },
    )


# Runs at import time too (not just "python app.py"), so gunicorn — which
# imports this module rather than executing it as __main__ — still creates
# the database tables on startup.
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)