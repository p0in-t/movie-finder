import os
import psycopg2
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from dotenv import load_dotenv
from llm import init_llm
from movie_similarity_search import load_or_build_index
from dataclasses import dataclass, field
from llm import MovieSearchTool
from sentence_transformers import SentenceTransformer
import sys
import uuid
import time
from threading import Lock
import atexit

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')
CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173", "https://movie-finder-ivory.vercel.app"], supports_credentials=True)

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

chat_sessions = {}
session_lock = Lock()

def get_or_create_session():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        print(f"Created new session: {session['session_id']}")
    
    session_id = session['session_id']
    
    with session_lock:
        if session_id not in chat_sessions:
            chat_sessions[session_id] = {
                'messages': [],
                'last_activity': time.time()
            }
            print(f"Initialized chat history for session: {session_id}")
        else:
            chat_sessions[session_id]['last_activity'] = time.time()
    
    return session_id

def get_session_messages(session_id):
    with session_lock:
        return chat_sessions.get(session_id, {}).get('messages', [])

def update_session_messages(session_id, messages):
    with session_lock:
        if session_id in chat_sessions:
            chat_sessions[session_id]['messages'] = messages
            chat_sessions[session_id]['last_activity'] = time.time()

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

def initialize_system():
    print("Connecting to database...")
    conn = get_db_connection()
    cursor = conn.cursor()
    # conn = None
    # cursor = None
    print("Loading index and movie dataframe...")
    movie_df, faiss_index = load_or_build_index(conn, cursor)
    print("Loading model...")
    sbert_model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
    print("Initializing movie search tool...")
    movie_search_tool = MovieSearchTool(faiss_index=faiss_index, movie_df=movie_df, model=sbert_model)
    print("Initializing LLM...")
    agent, graph = init_llm(movie_search_tool)
    print("EVerything initialized!")

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

@app.route('/api/process', methods=['POST'])
def process_data():
    print("Entered /api/process route.")
    
    session_id = get_or_create_session()
    
    data_from_frontend = request.get_json(silent=True)

    if data_from_frontend is None:
        print("ERROR: Failed to decode JSON from request body.")
        return jsonify({"error": "Invalid JSON or Content-Type header not set to application/json"}), 400
    
    print(f"Received data from frontend: {data_from_frontend}")
    print(f"Processing for session: {session_id}")
    
    user_prompt = data_from_frontend.get('prompt')

    if not user_prompt:
        print("ERROR: 'prompt' key not found in JSON.")
        return jsonify({"error": "Missing 'prompt' in request body"}), 400

    print("Passing to LLM")

    try:
        session_messages = get_session_messages(session_id)
        
        response = app_state.graph.invoke({
            "input": user_prompt,
            "messages": session_messages
        }, {"recursion_limit": 50})
        
        print("Got response from LLM:")
        print(response)
        
        if "messages" in response:
            update_session_messages(session_id, response["messages"])
        
        final_answer = ""
        if "final_answer" in response:
            if isinstance(response["final_answer"], dict) and "output" in response["final_answer"]:
                final_answer = response["final_answer"]["output"]
            else:
                final_answer = str(response["final_answer"])
        
        return jsonify({"result": final_answer})
        
    except Exception as e:
        print(f"ERROR: An exception occurred during LLM invocation: {e}")
        return jsonify({"error": "An internal error occurred while processing the request."}), 500

def on_shutdown():
    print("Server is shutting down. Performing cleanup...")
    global chat_sessions
    print(f"In-memory chat sessions will be lost. Found {len(chat_sessions)} sessions.")

atexit.register(on_shutdown)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    if initialize_system():
        app.run(host="0.0.0.0", port=port)
    else:
        exit(1)