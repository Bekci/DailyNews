import boto3
import db
import hmac
import json
import logging
import os
import secrets
import uuid
from datetime import datetime
from typing import Literal

from agent import Ulak
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from mangum import Mangum
from pydantic import BaseModel, ValidationError
from botocore.exceptions import ClientError
from secret_manager import get_key_from_ssm

load_dotenv()
DOWNLOAD_EXPIRES_IN = 60 * 3  # 3 minutes
PLAYBACK_EXPIRES_IN = 60 * 60
TOKEN_INVALIDATION_TIME = 60 * 60 # 1 hour
app = FastAPI()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("Initialized app!")
_chat_agent = None

def get_chat_agent():
    """Lazily initialize chat agent on first use."""
    global _chat_agent
    if _chat_agent is None:
        logger.info("Initializing chat agent...")
        _chat_agent = Ulak()
        logger.info("Chat agent initialized!")
    return _chat_agent

logger.info("Chat agent lazy-load configured!")

# Initialize API token once at startup
API_TOKEN = get_key_from_ssm(os.environ.get('API_TOKEN_PARAM_NAME'))

class ChatRequest(BaseModel):
    conversation_id: str
    message: str

class ChatResponse(BaseModel):
    conversation_id: str
    response: str
    documents: list[str] | None = None

class MessageResponse(BaseModel):
    role: str
    message: str
    created_at: int

class ConversationResponse(BaseModel):
    conversation_id: str
    messages: list[MessageResponse]

class ConversationCreateResponse(BaseModel):
    conversation_id: str
    first_question: str
    created_at: int

class ConversationHistoryResponse(BaseModel):
    conversations: list[ConversationCreateResponse]

class ConversationRequest(BaseModel):
    message: str

class DownloadLinkRequest(BaseModel):
    date_str: str

class DownloadLinkResponse(BaseModel):
    download_url: str | None
    message: str

class PlaybackSegment(BaseModel):
    text: str
    start_ms: int
    end_ms: int

class PlaybackResponse(BaseModel):
    audio_url: str
    segments: list[PlaybackSegment]

class LoginRequest(BaseModel):
    password: str

@app.middleware("http")
async def auth_middleware(request, call_next):
    # Allow login endpoint without authentication
    if request.url.path == "/login":
        return await call_next(request)
    
    auth = request.headers.get("authorization")
    try:
        auth_token = auth.split(" ")[1] if auth else None
        tokens = db.get_tokens_by_user("test_user")
    
        if not tokens:
            raise HTTPException(status_code=401, detail="No valid tokens found for user")
    
        latest_token = tokens[0]
    
        if not hmac.compare_digest(auth_token, latest_token['token']):
            raise HTTPException(status_code=401, detail="Invalid token")

        if int(datetime.now().timestamp()) - latest_token['created_at'] > TOKEN_INVALIDATION_TIME:
            raise HTTPException(status_code=401, detail="Token expired")

    except (IndexError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    return await call_next(request)    


@app.post("/login")
def login(request: LoginRequest):
    """
    Simple login endpoint that checks the provided password against the API token.
    """
    
    if not hmac.compare_digest(request.password, API_TOKEN):
        logger.info("Login attempt failed!")
        raise HTTPException(status_code=401, detail="Wrong Password")
    
    token = secrets.token_urlsafe(32)

    db.save_token_of_user("test_user", token)

    logger.info("Login attempt success!")
    return {"access_token": token, "message": "Login successful"}


@app.get("/conversations", response_model=ConversationHistoryResponse)
async def get_conversations():
    """
    Returns the list of conversations for a user.
    Each conversation includes an id, timestamp, and first question.
    """
    logger.info("/conversations called!")
    try:
        conversations = db.get_conversations_by_user("test_user")
        return ConversationHistoryResponse(conversations=conversations)
    except Exception as e:
        logger.error(f"Error fetching conversations: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch conversations")


@app.get("/messages/{conversation_id}", response_model=ConversationResponse)
async def get_messages(conversation_id: str):
    """
    Returns all messages for a given conversation.
    """
    messages = db.get_messages_by_conversation(conversation_id)
    return {"conversation_id": conversation_id, "messages": messages}


@app.post("/startchat", response_model=ConversationCreateResponse)
def start_chat(request: ConversationRequest):
    """
    Generates a new conversation with a unique ID and saves the first question.
    Must be called before /chat endpoint.
    """
    conversation_id = str(uuid.uuid4())
    conversation_created_at = db.save_conversation(conversation_id, "test_user", request.message)
    return ConversationCreateResponse(
        conversation_id=conversation_id, 
        first_question=request.message, 
        created_at=conversation_created_at)


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Sends a message to the chat agent and returns the response along with any referenced documents.
    """    
    db.save_message(request.conversation_id, "user", request.message)

    agent = get_chat_agent()
    response, documents = agent.query(request.message)

    db.save_message(request.conversation_id, "assistant", response)

    return ChatResponse(
        conversation_id=request.conversation_id,
        response=response,
        documents=documents
    )


@app.get("/download-options", response_model=list[str])
def get_download_options():
    """
    Returns a list of available dates for which audio files can be downloaded.
    """
    logger.info("/download-options called!")
    date_today = datetime.today()
    conn = boto3.client('s3')
    existing_file_keys = [key['Key'] for key in conn.list_objects(Bucket=os.environ["BUCKET_NAME"], Prefix=f'outputs/{date_today.year}/')['Contents'] if 'news.wav' in key['Key']]
    existing_dates = []
    for file_key in existing_file_keys:
        parts = file_key.split('/')
        if len(parts) >= 5:
            year, month, day = parts[1], parts[2], parts[3]
            existing_dates.append(f"{year}-{month.zfill(2)}-{day.zfill(2)}")
    existing_dates.sort()
    return existing_dates


@app.get("/playback-options", response_model=list[str])
def get_playback_options(language: Literal["german", "turkish"] = Query(...)):
    """Return dates with generated audio available for the selected language."""
    date_today = datetime.today()
    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")
    audio_name = f"{language}_news.wav"
    available_dates = set()

    for page in paginator.paginate(
        Bucket=os.environ["BUCKET_NAME"],
        Prefix=f"outputs/{date_today.year}/",
    ):
        for item in page.get("Contents", []):
            key = item["Key"]
            if not key.endswith(f"/{audio_name}"):
                continue

            parts = key.split("/")
            if len(parts) < 5:
                continue

            year, month, day = parts[1:4]
            try:
                available_date = datetime(int(year), int(month), int(day))
            except ValueError:
                logger.warning("Ignoring audio object with invalid date path: %s", key)
                continue
            available_dates.add(available_date.strftime("%Y-%m-%d"))

    return sorted(available_dates)


@app.get("/playback/{date_str}/{language}", response_model=PlaybackResponse)
def get_playback(date_str: str, language: Literal["german", "turkish"]):
    """Return a signed audio URL and its timed transcript for a generated date."""
    try:
        date_requested = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    date_prefix = (
        f"outputs/{date_requested.year}/{date_requested.month}/{date_requested.day}"
    )
    audio_key = f"{date_prefix}/{language}_news.wav"
    metadata_key = f"{date_prefix}/{language}_output_metadata.json"
    s3 = boto3.client("s3")

    try:
        s3.head_object(Bucket=os.environ["BUCKET_NAME"], Key=audio_key)
        metadata_response = s3.get_object(
            Bucket=os.environ["BUCKET_NAME"],
            Key=metadata_key,
        )
        metadata_bytes = metadata_response["Body"].read()
    except ClientError as error:
        error_code = error.response.get("Error", {}).get("Code")
        if error_code in {"404", "NoSuchKey", "NotFound"}:
            raise HTTPException(status_code=404, detail="Audio or transcript not found.")
        if error_code in {"403", "AccessDenied"}:
            raise HTTPException(status_code=403, detail="Access denied to audio or transcript.")
        logger.exception("Failed to load playback assets for %s", date_str)
        raise HTTPException(status_code=500, detail="Failed to load playback assets.")

    try:
        metadata = json.loads(metadata_bytes.decode("utf-8"))
        playback = PlaybackResponse(
            audio_url=s3.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": os.environ["BUCKET_NAME"],
                    "Key": audio_key,
                    "ResponseContentType": "audio/wav",
                },
                ExpiresIn=PLAYBACK_EXPIRES_IN,
            ),
            segments=metadata,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValidationError):
        logger.exception("Invalid playback metadata in S3 object %s", metadata_key)
        raise HTTPException(status_code=500, detail="Playback transcript is invalid.")

    return playback


@app.post("/download", response_model=DownloadLinkResponse)
def download_link(request: DownloadLinkRequest):
    """
    Generates a presigned S3 download link for the file generated on the given date.
    """
    
    s3 = boto3.client("s3")
    
    # Checking if the input is correct
    try:
        date_requested = datetime.strptime(request.date_str, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    key_in_bucket = f"outputs/{date_requested.year}/{date_requested.month}/{date_requested.day}/news.wav"

    # Checking if the file exists and can be accessed
    try:
        s3.head_object(Bucket=os.environ["BUCKET_NAME"], Key=key_in_bucket)
    except ClientError as e:
        error_code = e.response["Error"]["Code"]

        if error_code == "404":
            raise HTTPException(status_code=404, detail="File not found in S3")
        elif error_code == "403":
            raise HTTPException(status_code=403, detail="Access denied to S3 object")
        else:
            raise HTTPException(status_code=500, detail="Error checking file existence")

    download_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": os.environ["BUCKET_NAME"], "Key": key_in_bucket},
        ExpiresIn=DOWNLOAD_EXPIRES_IN
    )
    return DownloadLinkResponse(
        download_url=download_url,
        message="Download link generated successfully."
    )


handler = Mangum(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
