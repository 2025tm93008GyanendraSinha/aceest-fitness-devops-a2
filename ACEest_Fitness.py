"""ACEest Fitness & Gym - Modular Flask Web Application (Version 2.0)."""

import os
import socket
import sqlite3
from flask import Flask, jsonify, render_template, request

APP_VERSION = os.getenv("APP_VERSION", "v2.1")
DB_PATH = os.getenv("ACEEST_DB_PATH", "aceest_fitness.db")
DEFAULT_ADMIN_USER = os.getenv("ACEEST_ADMIN_USER", "admin")
DEFAULT_ADMIN_KEY = os.getenv("ACEEST_ADMIN_KEY", "admin")

app = Flask(__name__)


def get_db_connection(db_path=None):
    """Return a SQLite connection configured with row factory."""
    target_db = db_path or app.config.get("DATABASE", DB_PATH)
    conn = sqlite3.connect(target_db)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path=None):
    """Initialize SQLite tables for clients and workout programs."""
    with get_db_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                program TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Active'
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                duration_mins INTEGER NOT NULL DEFAULT 30
            )
            """
        )
        conn.commit()


@app.route("/", methods=["GET"])
def home():
    """Render the main gym dashboard with version, clients, and workouts."""
    init_db()
    with get_db_connection() as conn:
        client_rows = conn.execute(
            "SELECT id, name, program, status FROM clients ORDER BY id ASC"
        ).fetchall()
        workout_rows = conn.execute(
            "SELECT id, title, category, duration_mins FROM workouts ORDER BY id ASC"
        ).fetchall()
    return render_template(
        "index.html",
        version=APP_VERSION,
        hostname=socket.gethostname(),
        clients=[dict(row) for row in client_rows],
        workouts=[dict(row) for row in workout_rows],
    )


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for Docker and Kubernetes probes."""
    return jsonify({"status": "healthy", "version": APP_VERSION}), 200


@app.route("/version", methods=["GET"])
def version_info():
    """Return application version, pod hostname, and enabled features."""
    return jsonify(
        {
            "app": "ACEest Fitness & Gym",
            "version": APP_VERSION,
            "hostname": socket.gethostname(),
            "features": [
                "client-management",
                "health-probe",
                "workout-plans",
                "gym-stats",
            ],
        }
    ), 200


@app.route("/login", methods=["POST"])
def login():
    """Authenticate gym administrator credentials."""
    payload = request.get_json(silent=True) or {}
    username = payload.get("username", "").strip()
    access_key = payload.get("password", "").strip()

    if username == DEFAULT_ADMIN_USER and access_key == DEFAULT_ADMIN_KEY:
        return jsonify({"message": "Login successful", "user": username}), 200
    return jsonify({"error": "Invalid credentials"}), 401


@app.route("/clients", methods=["GET"])
def list_clients():
    """Return all registered gym clients as JSON."""
    init_db()
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, program, status FROM clients ORDER BY id ASC"
        ).fetchall()
    return jsonify([dict(row) for row in rows]), 200


@app.route("/clients", methods=["POST"])
def add_client():
    """Register a new gym client."""
    payload = request.get_json(silent=True) or {}
    name = payload.get("name", "").strip()
    program = payload.get("program", "").strip()
    status = payload.get("status", "Active").strip() or "Active"

    if not name or not program:
        return jsonify({"error": "Both 'name' and 'program' are required"}), 400

    init_db()
    with get_db_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO clients (name, program, status) VALUES (?, ?, ?)",
            (name, program, status),
        )
        conn.commit()
        client_id = cursor.lastrowid

    return jsonify(
        {
            "id": client_id,
            "name": name,
            "program": program,
            "status": status,
            "version": APP_VERSION,
        }
    ), 201


@app.route("/workouts", methods=["GET"])
def list_workouts():
    """Return all available workout programs as JSON."""
    init_db()
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT id, title, category, duration_mins FROM workouts ORDER BY id ASC"
        ).fetchall()
    return jsonify([dict(row) for row in rows]), 200


@app.route("/workouts", methods=["POST"])
def add_workout():
    """Create a new workout program."""
    payload = request.get_json(silent=True) or {}
    title = payload.get("title", "").strip()
    category = payload.get("category", "").strip()
    duration_mins = payload.get("duration_mins", 30)

    if not title or not category:
        return jsonify({"error": "Both 'title' and 'category' are required"}), 400

    if (
        isinstance(duration_mins, bool)
        or not isinstance(duration_mins, int)
        or duration_mins <= 0
    ):
        return jsonify({"error": "'duration_mins' must be a positive integer"}), 400

    init_db()
    with get_db_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO workouts (title, category, duration_mins) VALUES (?, ?, ?)",
            (title, category, duration_mins),
        )
        conn.commit()
        workout_id = cursor.lastrowid

    return jsonify(
        {
            "id": workout_id,
            "title": title,
            "category": category,
            "duration_mins": duration_mins,
            "version": APP_VERSION,
        }
    ), 201


@app.route("/stats", methods=["GET"])
def gym_stats():
    """Return summary counts of registered clients and workout programs."""
    init_db()
    with get_db_connection() as conn:
        client_count = conn.execute(
            "SELECT COUNT(*) FROM clients"
        ).fetchone()[0]
        workout_count = conn.execute(
            "SELECT COUNT(*) FROM workouts"
        ).fetchone()[0]
    return jsonify(
        {
            "version": APP_VERSION,
            "total_clients": client_count,
            "total_workouts": workout_count,
        }
    ), 200


if __name__ == "__main__":
    init_db()
    host = os.getenv("FLASK_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_PORT", "5000"))
    app.run(host=host, port=port, debug=False)
