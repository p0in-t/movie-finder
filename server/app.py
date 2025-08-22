import os
import re
from typing import Dict, List
import psycopg2
from dotenv import load_dotenv
from llm import init_llm
from movie_similarity_search import cloud_load_or_build, load_or_build_index
from dataclasses import dataclass, field
from llm import MovieSearchTool
from sentence_transformers import SentenceTransformer
import sys
import uuid
import time
from google.cloud import storage
import bcrypt
from cryptography.fernet import Fernet
from fastapi import APIRouter, FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
import jwt
from jwt import PyJWTError
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, EmailStr, Field
from contextlib import asynccontextmanager

load_dotenv()

APP_ENV = os.environ.get('APP_ENV')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

if (APP_ENV == 'debug'):
    DATABASE_URL  = os.environ.get('DATABASE_URL_DEBUG')
else:
    DATABASE_URL  = os.environ.get('DATABASE_URL')

BUCKET_NAME = 'movies-db-bucket'
MODEL_GCS_PREFIX = 'sbert_model/'
LOCAL_MODEL_PATH = './sbert_model'

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not initialize_system():
        print("FATAL: System initialization failed. Exiting.")
        sys.exit(1)
    print("System initialized successfully.")
    
    yield
    
    print("Server is shutting down. Performing cleanup...")

app = FastAPI(lifespan=lifespan, debug=True, title="MovieFinder", summary="Made with love from ModelIntellect", version="0.0.1")
user_router = APIRouter(prefix="/api/users", tags=["users"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


if (APP_ENV == 'debug'):
    origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
else:
    origins = [
        "https://movie-finder-ivory.vercel.app"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    result: bool = True

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)

class SignupResponse(BaseModel):
    message: str
    user_id: str
    result: bool = True

class SessionItem(BaseModel):
    session_id: str
    started_at: str
    title: str

class GetSessionsResponse(BaseModel):
    sessions: List[SessionItem]
    result: bool = True

class Message(BaseModel):
    id: int
    sender: str
    message: str
    sent_at: str

class GetChatRequest(BaseModel):
    session_id: str

class GetChatResponse(BaseModel):
    messages: List[Message]
    result: bool = True

class ProcessRequest(BaseModel):
    prompt: str
    session_id: str

class ProcessResponse(BaseModel):
    answer: str
    result: bool = True

class GetStartSessionResponse(BaseModel):
    session_id: str
    result: bool = True

FERNET_KEY = os.environ.get('FERNET_KEY')

if not FERNET_KEY:
    raise ValueError("FERNET_KEY environment variable not set")

fernet = Fernet(FERNET_KEY)

def create_access_token(data, expires_delta):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, os.environ.get('JWT_SECRET_KEY'), algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, os.environ.get('JWT_SECRET_KEY'), algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")

        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        return payload
    except PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid credentials")

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

def get_session_messages(session_id: str, user_id: str):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id FROM chat_session
            WHERE id = %s AND user_id = %s;
        """, (session_id, user_id))

        session_check = cur.fetchone()

        if not session_check:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, description="Session not found or unauthorized")

        cur.execute("""
            SELECT id, sender, message, sent_at
            FROM chat_message
            WHERE session_id = %s
            ORDER BY id ASC;
        """, (session_id,))

        messages = cur.fetchall()

        message_list = [
            {"id": row[0], "sender": row[1], "message": row[2], "sent_at": row[3].isoformat()}
            for row in messages
        ]

        return { "messages": message_list }

    except Exception as e:
        print(f"Error retrieving chat messages: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, description="Internal server error")
    finally:
        cur.close()
        conn.close()

def get_db_connection():
    try:
        print("Attempting to connect to the database...")
        conn = psycopg2.connect(DATABASE_URL)
        
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
    print("Loading index and movie dataframe...")

    if (APP_ENV == 'debug'):
        movie_df, faiss_index = load_or_build_index(conn, cursor)
    else:
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

@user_router.get('/start-session', response_model=GetStartSessionResponse, status_code=status.HTTP_200_OK)
async def start_session(current_user = Depends(get_current_user)):
    user_id: str = current_user.get('sub')
    is_active: bool = current_user.get('is_active')
    email_verified: bool = current_user.get('email_verified')

    if (not email_verified or not is_active):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is not authorized")

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO chat_session (user_id)
            VALUES (%s)
            RETURNING id;
        """, (user_id,))
        session_id: str = cur.fetchone()[0]
        conn.commit()

        return GetStartSessionResponse(session_id=session_id)
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error starting new session: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Server error")
    finally:
        cur.close()
        conn.close()

@user_router.get('/get-sessions', response_model=GetSessionsResponse, status_code=status.HTTP_200_OK)
async def get_sessions(current_user = Depends(get_current_user)):
    user_id: str = current_user.get('sub')

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
            {"session_id": row[0], "started_at": row[1].isoformat() if hasattr(row[1], 'isoformat') else str(row[1]), "title": row[2]}
            for row in sessions
        ]

        return GetSessionsResponse(sessions=session_list)
    except Exception as e:
        print(f"Error getting sessions: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Server error")
    finally:
        cur.close()
        conn.close()

@user_router.post('/get-chat', response_model=GetChatResponse, status_code=status.HTTP_200_OK)
async def get_chat_messages(user_data: GetChatRequest, current_user = Depends(get_current_user)):
    user_id: str = current_user.get('sub')
    
    session_id = user_data.session_id

    if not session_id:
        raise HTTPException(status_code=400, detail="Missing session_id")
    
    res = get_session_messages(session_id, user_id)

    return GetChatResponse(messages=res.get('messages'))

@user_router.post('/sign-up', response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
async def user_create(user_data: SignupRequest):
    password_hash = bcrypt.hashpw(user_data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    raw_username = user_data.email.split("@")[0]
    username = re.sub(r'\W+', '', raw_username)

    conn = get_db_connection()

    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed.")
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO public.users (username, email, password_hash, is_active, email_verified)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id;
                """, (username, user_data.email, password_hash, True, True))

                user_id = cur.fetchone()[0]

        return SignupResponse(message="User created successfully.", user_id=user_id)

    except psycopg2.IntegrityError:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=409, detail="Username or email already exists.")
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        conn.close()

@user_router.post('/log-in', response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def user_login(user_data: LoginRequest):
    email = user_data.email
    password = user_data.password

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
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

        user_id, username, password_hash, gemini_api_key, is_active, is_admin, email_verified = user

        if gemini_api_key is None:
            has_gemini_api_key = False
        else:
            has_gemini_api_key = True

        if isinstance(password_hash, memoryview):
            password_hash = password_hash.tobytes().decode('utf-8')

        if not bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

        print("Logged in!")

        token_data = {
            "sub": str(user_id),
            "username": username,
            "is_active": is_active,
            "is_admin": is_admin,
            "email_verified": email_verified,
        }

        access_token = create_access_token(data=token_data, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))

        return LoginResponse(access_token=access_token)
    except Exception as e:
        print(f"Login error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
    finally:
        cur.close()
        conn.close()

@user_router.get("/auth-status")
async def auth_status(current_user = Depends(get_current_user)):
    return {
        "result": True,
        "sub": current_user.get("sub"),
        "username": current_user.get("username"),
        "is_active": current_user.get("is_active"),
        "is_admin": current_user.get("is_admin"),
        "email_verified": current_user.get("email_verified"),
    }

@app.post('/api/user/log-out')
async def user_logout(token: str = Depends(oauth2_scheme)):
    return {"message": "Logout successful", "result": True}

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

@app.post('/api/process', response_model=ProcessResponse, status_code=status.HTTP_200_OK)
async def process_data(data: ProcessRequest, current_user = Depends(get_current_user)):
    user_id: str = current_user.get('sub')
    user_prompt = data.prompt
    session_id = data.session_id

    conn = None
    cur = None
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id FROM chat_session
            WHERE id = %s AND user_id = %s;
        """, (session_id, user_id))

        session_check = cur.fetchone()
        if not session_check:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session not found or unauthorized")

        cur.execute("""
            INSERT INTO chat_message (session_id, sender, message)
            VALUES (%s, %s, %s);
        """, (session_id, "user", user_prompt))

        session_messages_result = get_session_messages(session_id, user_id)

        messages_list = session_messages_result.get("messages", [])
        session_messages = format_chat_history(messages_list)

        response = app_state.graph.invoke({
            "input": user_prompt,
            "messages": session_messages
        }, {"recursion_limit": 50})

        final_answer = response.get("final_answer")
        if final_answer is None:
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="LLM returned no answer")

        if isinstance(final_answer, dict) and "output" in final_answer:
            final_answer = final_answer["output"]
        else:
            final_answer = str(final_answer)

        cur.execute("""
            INSERT INTO chat_message (session_id, sender, message)
            VALUES (%s, %s, %s);
        """, (session_id, "ai", final_answer))

        conn.commit()

        return ProcessResponse(answer=final_answer)

    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Internal error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
    
# @app.get('/api/user/get-api-key')
# async def get_user_api_key():
#     if not session.get('logged_in'):
#         return jsonify({"error": "Unauthorized", "result": False}), 401
    
#     if not session.get('has_gemini_api_key'):
#         return jsonify({"api_key": None, "result": True})

#     user_id = session.get('user_id')

#     if not user_id:
#         return jsonify({"error": "Unauthorized", "result": False}), 401

#     try:
#         conn = get_db_connection()
#         cur = conn.cursor()
#         cur.execute("SELECT gemini_api_key FROM users WHERE id = %s", (user_id,))
#         result = cur.fetchone()

#         if result and result[0]:
#             decrypted_key = decrypt_api_key(result[0])
#             return jsonify({"api_key": decrypted_key, "result": True})
#         else:
#             return jsonify({"api_key": None, "result": True})

#     except Exception as e:
#         print("Error retrieving API key:", e)
#         return jsonify({"error": "Server error", "result": False}), 500

#     finally:
#         cur.close()
#         conn.close()

# @app.post('/api/user/update-settings')
# async def update_user_settings():
#     print("printing session: ", session, "\nlogged in: ", session.get("logged_in"))

#     if not session.get('logged_in'):
#         return jsonify({"error": "Unauthorized", "result": False}), 401
    
#     user_id = session.get('user_id')
#     data = request.get_json()

#     if not data:
#         return jsonify({"error": "No data provided", "result": False}), 400

#     allowed_fields = ['username', 'password_hash', 'gemini_api_key']
#     fields_to_update = {}
    
#     for key in data:
#         if key in allowed_fields:
#             fields_to_update[key] = data[key]

#     if not fields_to_update:
#         return jsonify({"error": "No valid fields to update", "result": False}), 400
    
#     set_clauses = []
#     values = []
#     for i, (field, value) in enumerate(fields_to_update.items(), start=1):
#         set_clauses.append(f"{field} = %s")
#         values.append(value)

#     set_clause = ", ".join(set_clauses)
#     values.append(user_id)

#     query = f"UPDATE users SET {set_clause} WHERE id = %s"

#     try:
#         conn = get_db_connection()
#         cur = conn.cursor()
#         cur.execute(query, values)
#         conn.commit()
#         return jsonify({"message": "Settings updated", "result": True})
#     except Exception as e:
#         if conn:
#             conn.rollback()
#         print(f"Error updating user settings: {e}")
#         return jsonify({"error": "Internal server error", "result": False}), 500
#     finally:
#         cur.close()
#         conn.close())

app.include_router(user_router)