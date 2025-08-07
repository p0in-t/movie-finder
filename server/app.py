import os
import psycopg2
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from dotenv import load_dotenv
from llm import init_llm
from movie_similarity_search import cloud_load_or_build, load_or_build_index
from dataclasses import dataclass, field
from llm import MovieSearchTool
from sentence_transformers import SentenceTransformer
import sys
import uuid
import time
from threading import Lock
import atexit
from google.cloud import storage
import bcrypt
from cryptography.fernet import Fernet

load_dotenv()

BUCKET_NAME = 'movies-db-bucket'
MODEL_GCS_PREFIX = 'sbert_model/'
LOCAL_MODEL_PATH = './sbert_model'

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')
CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173", "https://movie-finder-ivory.vercel.app"], supports_credentials=True)
app.config.update(SESSION_COOKIE_SAMESITE="None", SESSION_COOKIE_SECURE=True)

FERNET_KEY = os.environ.get('FERNET_KEY')

if not FERNET_KEY:
    raise ValueError("FERNET_KEY environment variable not set")

fernet = Fernet(FERNET_KEY)

@dataclass
class AppState:
    movie_df: object = field(default=None)
    faiss_index: object = field(default=None)
    agent: object = field(default=None)
    graph: object = field(default=None)
    model: object = field(default=None)
    is_initialized: bool = False

    def __post_init__(self):
        if self.faiss_index is not None and self.movie_df is not None and self.agent is not None and self.graph is not None:
            self.is_initialized = True

app_state = AppState()

def load_model_from_gcs():
    if os.path.exists(LOCAL_MODEL_PATH):
        print(f"Found model locally at {LOCAL_MODEL_PATH}. Loading from disk.")
        return SentenceTransformer(LOCAL_MODEL_PATH, device='cpu')

    print(f"Model not found locally. Downloading from gs://{BUCKET_NAME}/{MODEL_GCS_PREFIX}")

    os.makedirs(LOCAL_MODEL_PATH, exist_ok=True)

    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)

        blobs = bucket.list_blobs(prefix=MODEL_GCS_PREFIX)

        for blob in blobs:
            if blob.name.endswith('/'):
                continue

            relative_path = blob.name[len(MODEL_GCS_PREFIX):]
            local_file_path = os.path.join(LOCAL_MODEL_PATH, relative_path)

            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            
            print(f"Downloading {blob.name} to {local_file_path}...")
            blob.download_to_filename(local_file_path)

        print("Model download complete.")

    except Exception as e:
        print(f"ERROR: Failed to download model from GCS. {e}")
        raise RuntimeError(f"Could not download model from GCS: {e}")

    print(f"Loading model from newly downloaded files at {LOCAL_MODEL_PATH}")
    return SentenceTransformer(LOCAL_MODEL_PATH, device='cpu')

def get_session_messages(session_id, user_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id FROM chat_session
            WHERE id = %s AND user_id = %s;
        """, (session_id, user_id))

        session_check = cur.fetchone()

        if not session_check:
            return {"error": "Session not found or unauthorized", "result": False}

        cur.execute("""
            SELECT id, sender, message, sent_at
            FROM chat_message
            WHERE session_id = %s
            ORDER BY id ASC;
        """, (session_id,))

        messages = cur.fetchall()

        message_list = [
            {"id": row[0], "sender": row[1], "message": row[2], "sent_at": row[2].isoformat()}
            for row in messages
        ]

        return { "messages": message_list, "result": True }

    except Exception as e:
        print(f"Error retrieving chat messages: {e}")
        return {"error": "Server error", "result": False}
    finally:
        cur.close()
        conn.close()

def get_db_connection():
    try:
        print("Attempting to connect to the database...")
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        
        print(f"Connection successful. Status: {conn.status}")
        
        if conn.closed == 0:
            print("Connection is open and ready to use.")
            return conn
        else:
            print("Connection was established but is closed.", file=sys.stderr)
            return None

    except psycopg2.OperationalError as e:
        print(f"ERROR: Could not connect to the database. OperationalError: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"ERROR: An unexpected error occurred: {e}", file=sys.stderr)
        return None

def encrypt_api_key(api_key):
    encrypted_bytes = fernet.encrypt(api_key.encode('utf-8'))
    return encrypted_bytes.decode('utf-8')

def decrypt_api_key(encrypted_key):
    decrypted_bytes = fernet.decrypt(encrypted_key)
    return decrypted_bytes.decode('utf-8')

def initialize_system():
    print("Connecting to database...")
    conn = get_db_connection()
    cursor = conn.cursor()
    # conn = None
    # cursor = None
    print("Loading index and movie dataframe...")
    movie_df, faiss_index = cloud_load_or_build(conn, cursor)
    print("Loading model...")
    sbert_model = load_model_from_gcs()
    print("Initializing movie search tool...")
    movie_search_tool = MovieSearchTool(faiss_index=faiss_index, movie_df=movie_df, model=sbert_model)
    print("Initializing LLM...")
    agent, graph = init_llm(movie_search_tool)
    print("Everything initialized!")

    cursor.close()
    conn.close()

    global app_state
    app_state = AppState(
        movie_df=movie_df,
        faiss_index=faiss_index,
        agent=agent,
        graph=graph,
        model=sbert_model
    )

    return app_state.is_initialized

@app.route('/api/user/start-session', methods=['GET'])
def start_session():
    print("printing session: ", session, "\nlogged in: ", session.get("logged_in"))

    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized", "result": False}), 401

    user_id = session.get('user_id')

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO chat_session (user_id)
            VALUES (%s)
            RETURNING id;
        """, (user_id,))
        session_id = cur.fetchone()[0]
        conn.commit()
        return jsonify({"session_id": session_id, "result": True})
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error starting new session: {e}")
        return jsonify({"error": "Server error", "result": False}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/api/user/get-sessions', methods=['GET'])
def get_sessions():
    print("printing session: ", session, "\nlogged in: ", session.get("logged_in"))

    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized", "result": False}), 401

    user_id = session.get('user_id')

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, started_at, title
            FROM chat_session
            WHERE user_id = %s
            ORDER BY started_at DESC;
        """, (user_id,))

        sessions = cur.fetchall()

        session_list = [
            {"session_id": row[0], "started_at": row[1], "title": row[2]}
            for row in sessions
        ]

        return jsonify({"sessions": session_list, "result": True})
    except Exception as e:
        print(f"Error starting new session: {e}")
        return jsonify({"error": "Server error", "result": False}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/api/user/get-chat', methods=['POST'])
def get_chat_messages():
    print("printing session: ", session, "\nlogged in: ", session.get("logged_in"))

    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized", "result": False}), 401

    user_id = session.get('user_id')
    data = request.get_json(silent=True)

    if data is None:
        print("ERROR: Failed to decode JSON from request body.")
        return jsonify({"error": "Invalid JSON or Content-Type header not set to application/json", "result": False}), 400
    
    session_id = data.get('session_id')

    if not session_id:
        return jsonify({"error": "Missing session_id", "result": False}), 400
    
    result = get_session_messages(session_id, user_id)

    return jsonify(result)

@app.route('/api/user/sign-up', methods=['POST'])
def user_create():
    print("printing session: ", session, "\nlogged in: ", session.get("logged_in"))

    user_data = request.get_json(silent=True)

    if user_data is None:
        print("ERROR: Failed to decode JSON from request body.")
        return jsonify({"error": "Invalid JSON or Content-Type header not set to application/json"}), 400
    
    required_fields = ['username', 'email', 'password']

    if not all(field in user_data for field in required_fields):
        return {"error": "Missing required fields."}, 400
    
    username = user_data.get('username')
    email = user_data.get('email')
    password = user_data.get('password')

    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    conn = get_db_connection()

    if conn is None:
        return {"error": "Database connection failed."}, 500
    
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO public.users (username, email, password_hash)
                    VALUES (%s, %s, %s)
                    RETURNING id;
                """, (username, email, password_hash))

                user_id = cur.fetchone()[0]
                return {"message": "User created successfully.", "user_id": user_id}, 201
    except psycopg2.IntegrityError as e:
        if conn:
            conn.rollback()
        return {"error": "Username or email already exists."}, 409
    except Exception as e:
        if conn:
            conn.rollback()
        return {"error": str(e)}, 500
    finally:
        conn.close()

@app.route('/api/user/log-in', methods=['POST'])
def user_login():
    print("printing session: ", session, "\nlogged in: ", session.get("logged_in"))

    user_data = request.get_json()

    if user_data is None:
        print("ERROR: Failed to decode JSON from request body.")
        return jsonify({"error": "Invalid JSON or Content-Type header not set to application/json", "result": False}), 400
    
    email = user_data.get('email')
    password = user_data.get('password')

    if not email or not password:
        return jsonify({
            "error": "Email and password required",
            "result": False
        }), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, username, password_hash, gemini_api_key, is_active, is_admin, email_verified
            FROM users
            WHERE email = %s
        """, (email,))

        user = cur.fetchone()

        if user is None:
            return jsonify({"error": "Invalid email or password", "result": False}), 401

        user_id, username, password_hash, gemini_api_key, is_active, is_admin, email_verified = user

        if gemini_api_key is None:
            has_gemini_api_key = False
        else:
            has_gemini_api_key = True

        if isinstance(password_hash, memoryview):
            password_hash = password_hash.tobytes().decode('utf-8')

        if not bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
            return jsonify({"error": "Invalid email or password", "result": False}), 401

        print("Logged in!")
        print("printing session: ", session, "\nlogged in: ", session.get("logged_in"))

        session['user_id'] = str(user_id)
        session['username'] = username
        session['logged_in'] = True
        session['is_active'] = is_active
        session['is_admin'] = is_admin
        session['email_verified'] = email_verified
        session['has_gemini_api_key'] = has_gemini_api_key

        session.modified = True


        print("printing session: ", session, "\nlogged in: ", session.get("logged_in"))

        return jsonify({
            "message": "Login successful",
            "user_id": str(user_id),
            "username": username,
            "is_active": is_active,
            "is_admin": is_admin,
            "email_verified": email_verified,
            "has_gemini_api_key": has_gemini_api_key,
            "result": True
        })
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({"error": "Internal server error", "result": False}), 500

    finally:
        cur.close()
        conn.close()

@app.route('/api/user/log-out', methods=['POST'])
def user_logout():
    print("printing session: ", session, "\nlogged in: ", session.get("logged_in"))
    
    if not session.get('logged_in'):
        return jsonify({"message": "No active session to log out from", "result": False}), 200

    session.clear()

    session.modified = True

    return jsonify({"message": "Logout successful", "result": True})

def format_chat_history(messages):
    formatted = []
    for msg in messages:
        sender = msg.get("sender", "").lower()
        if sender == "user":
            role = "User"
        elif sender == "ai":
            role = "AI"
        else:
            role = sender.capitalize() or "Unknown"

        content = msg.get("message", "")
        formatted.append(f"{role}: {content}")

    return formatted

@app.route('/api/process', methods=['POST'])
def process_data():
    print("printing session: ", session, "\nlogged in: ", session.get("logged_in"))
    print("Entered /api/process route.")
    
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized","result": False}), 401
        
    data_from_frontend = request.get_json(silent=True)

    if data_from_frontend is None:
        print("ERROR: Failed to decode JSON from request body.")
        return jsonify({"error": "Invalid JSON or Content-Type header not set to application/json", "result": False}), 400
    
    user_prompt = data_from_frontend.get('prompt')

    if not user_prompt:
            print("ERROR: 'prompt' key not found in JSON.")
            return jsonify({"error": "Missing 'prompt' in request body", "result": False}), 400
    
    session_id = data_from_frontend.get("session_id")
    
    print(f"Received data from frontend: {data_from_frontend}")
    print(f"Processing for session: {session_id}")
    
    user_id = session["user_id"]

    print("Passing to LLM")

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
                    SELECT id FROM chat_session
                    WHERE id = %s AND user_id = %s;
                """, (session_id, user_id))

        session_check = cur.fetchone()

        if not session_check:
            return jsonify({"error": "Session not found or unauthorized", "result": False}), 401

        cur.execute("""
            INSERT INTO chat_message (session_id, sender, message)
            VALUES (%s, %s, %s);
        """, (session_id, "user", user_prompt))

        try:
            session_messages_result = get_session_messages(session_id, user_id)
            session_messages = format_chat_history(session_messages_result)
            
            response = app_state.graph.invoke({
                "input": user_prompt,
                "messages": session_messages
            }, {"recursion_limit": 50})
            
            print("Got response from LLM:")
            print(response)

            final_answer = response["final_answer"]
            
            if final_answer is None:
                return jsonify({"error": "An internal error occurred while processing the request."}), 501
            
            if isinstance(response["final_answer"], dict) and "output" in response["final_answer"]:
                final_answer = response["final_answer"]["output"]
            else:
                final_answer = str(response["final_answer"])

            cur.execute("""
                INSERT INTO chat_message (session_id, sender, message)
                VALUES (%s, %s, %s);
            """, (session_id, "ai", final_answer))

            conn.commit()
            
            return jsonify({"answer": final_answer, "result": True})
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"ERROR: An exception occurred during LLM invocation: {e}")
            return jsonify({"error": "An internal error occurred while processing the request.", "result": False}), 500
    except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error occurred during chat history update: {e}")
            return jsonify({"error": "Internal server error", "result": False}), 500
    finally:
            cur.close()
            conn.close()
    
@app.route('/api/user/get-api-key', methods=['GET'])
def get_user_api_key():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized", "result": False}), 401
    
    if not session.get('has_gemini_api_key'):
        return jsonify({"api_key": None, "result": True})

    user_id = session.get('user_id')

    if not user_id:
        return jsonify({"error": "Unauthorized", "result": False}), 401

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT gemini_api_key FROM users WHERE id = %s", (user_id,))
        result = cur.fetchone()

        if result and result[0]:
            decrypted_key = decrypt_api_key(result[0])
            return jsonify({"api_key": decrypted_key, "result": True})
        else:
            return jsonify({"api_key": None, "result": True})

    except Exception as e:
        print("Error retrieving API key:", e)
        return jsonify({"error": "Server error", "result": False}), 500

    finally:
        cur.close()
        conn.close()

@app.route('/api/user/update-settings', methods=['POST'])
def update_user_settings():
    print("printing session: ", session, "\nlogged in: ", session.get("logged_in"))

    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized", "result": False}), 401
    
    user_id = session.get('user_id')
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided", "result": False}), 400

    allowed_fields = ['username', 'password_hash', 'gemini_api_key']
    fields_to_update = {}
    
    for key in data:
        if key in allowed_fields:
            fields_to_update[key] = data[key]

    if not fields_to_update:
        return jsonify({"error": "No valid fields to update", "result": False}), 400
    
    set_clauses = []
    values = []
    for i, (field, value) in enumerate(fields_to_update.items(), start=1):
        set_clauses.append(f"{field} = %s")
        values.append(value)

    set_clause = ", ".join(set_clauses)
    values.append(user_id)

    query = f"UPDATE users SET {set_clause} WHERE id = %s"

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, values)
        conn.commit()
        return jsonify({"message": "Settings updated", "result": True})
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error updating user settings: {e}")
        return jsonify({"error": "Internal server error", "result": False}), 500
    finally:
        cur.close()
        conn.close()

def on_shutdown():
    print("Server is shutting down. Performing cleanup...")

atexit.register(on_shutdown)

if not initialize_system():
    print("FATAL: System initialization failed. Exiting.")
    exit(1)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    if initialize_system():
        app.run(host="0.0.0.0", port=port)
    else:
        exit(1)