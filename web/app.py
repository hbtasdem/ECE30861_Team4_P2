#!/usr/bin/env python3
"""Flask web application for model scoring."""

import json
import os
import subprocess
import sys
import tempfile
from typing import Any, Tuple

from flask import Flask, jsonify, render_template, request
from flask.wrappers import Response

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

# Get paths relative to project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
SCORER_PATH = os.path.join(SRC_DIR, "main.py")


@app.route("/")
def index() -> Any:
    """Serve the main page."""
    return render_template("index.html")


@app.route("/api/score-model", methods=["POST"])
def score_model() -> Tuple[Response, int]:
    """Score a model from a HuggingFace URL."""
    data = request.json
    model_url = data.get("model_url", "").strip()

    if not model_url:
        return jsonify({"error": "model_url is required"}), 400

    # Check if scorer exists
    if not os.path.exists(SCORER_PATH):
        return jsonify({"error": f"main.py not found at {SCORER_PATH}"}), 500

    temp_file = None
    try:
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
            f.write(f",,{model_url}\n")
            temp_file = f.name

        # Run model scorer (main) with proper PYTHONPATH
        env = os.environ.copy()
        env["PYTHONPATH"] = PROJECT_ROOT  # Add project root to Python path

        result = subprocess.run(
            [sys.executable, SCORER_PATH, temp_file],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=SRC_DIR,  # Run from src directory
            env=env,  # Use modified environment
        )

        # Clean up temp file
        os.unlink(temp_file)
        temp_file = None

        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else "Unknown error"
            return jsonify({"error": error_msg}), 500

        # Parse JSON output
        output_lines = result.stdout.strip().split("\n")
        if not output_lines:
            return jsonify({"error": "No output from scorer"}), 500

        json_output = output_lines[-1]
        model_data = json.loads(json_output)

        return jsonify(model_data), 200

    except subprocess.TimeoutExpired:
        if temp_file and os.path.exists(temp_file):
            os.unlink(temp_file)
        return jsonify({"error": "Scoring timed out after 5 minutes"}), 504

    except json.JSONDecodeError as e:
        return jsonify({"error": f"Failed to parse output: {str(e)}"}), 500

    except Exception as e:
        if temp_file and os.path.exists(temp_file):
            os.unlink(temp_file)
        return jsonify({"error": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health() -> Tuple[Response, int]:
    """Health check endpoint."""
    return (
        jsonify(
            {
                "status": "ok",
                "scorer_path": SCORER_PATH,
                "scorer_exists": os.path.exists(SCORER_PATH),
            }
        ),
        200,
    )


if __name__ == "__main__":
    # Verify setup
    print("\n" + "=" * 60)
    print("🚀 Model Scorer Web Interface")
    print("=" * 60)
    print(f"\nProject Root: {PROJECT_ROOT}")
    print(f"Source Directory: {SRC_DIR}")
    print(f"Scorer Path: {SCORER_PATH}")

    if not os.path.exists(SCORER_PATH):
        print("\n WARNING: model_scorer.py not found!")
        print("\nExpected structure:")
        print(f"   {os.path.basename(PROJECT_ROOT)}/")
        print("   ├── src/")
        print("   │   ├── main.py")
        print("   │   └── ... (other metrics)")
        print("   └── web/")
        print("       ├── app.py")
        print("       └── templates/")
        print("           └── index.html")
        print("\nCannot start server without main.py\n")
        sys.exit(1)
    else:
        print("\nFound main.py")
        print("\nStarting server on http://localhost:5000")
        print("=" * 60 + "\n")

    app.run(debug=True, host="0.0.0.0", port=5000)
