import os
import boto3
import db
import uuid
import logging

from agent import Ulak
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI
from mangum import Mangum
from fastapi import HTTPException
from pydantic import BaseModel
from botocore.exceptions import ClientError
from secret_manager import get_key_from_ssm
load_dotenv()
DOWNLOAD_EXPIRES_IN = 60 * 3  # 3 minutes
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


@app.middleware("http")
async def auth_middleware(request, call_next):
    logger.info("Middleware received request!")
    auth = request.headers.get("authorization")

    if auth != f"Bearer {API_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    return await call_next(request)    


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