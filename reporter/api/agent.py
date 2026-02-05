import os
import logging

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.documents import Document
from langchain.agents.middleware import AgentMiddleware, AgentState
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langgraph.checkpoint.memory import InMemorySaver
from pinecone import Pinecone
from prompt import SYSTEM_PROMPT
from typing import Any
from secret_manager import get_key_from_ssm

load_dotenv()
logger = logging.getLogger(__name__)
os.environ["GOOGLE_API_KEY"] = get_key_from_ssm("google-api")

INDEX_NAME = "daily-news"
EMBED_MODEL_NAME = "gemini-embedding-001"
CHAT_MODEL_NAME = "gemini-2.5-flash-lite"


pc_store = Pinecone(api_key=get_key_from_ssm("pinecone-key"))
index = pc_store.Index(name=INDEX_NAME)
embedding_model = GoogleGenerativeAIEmbeddings(model=EMBED_MODEL_NAME)
vector_store = PineconeVectorStore(embedding=embedding_model, index=index)

class State(AgentState):
    context: list[Document]

class RetrieveDocumentsMiddleware(AgentMiddleware[State]):
    state_schema = State

    def before_model(self, state: AgentState) -> dict[str| Any] | None:
 
        last_query = state["messages"][-1]
        retrieved_docs = vector_store.similarity_search(last_query.content, k=5)
        
        docs_content = "\n\n".join(doc.page_content for doc in retrieved_docs)

        augmented_message_content = (
            f"{last_query.content}\n\n"
            f"Kullanıcının sorusunu cevaplamak için bu bilgileri kullan:\n\n"
            f"{docs_content}"
        )

        return {
            "messages": [last_query.model_copy(update={"content": augmented_message_content})],
            "context": retrieved_docs
        }


class Ulak:
    def __init__(self):
        logger.info("Initializing agent...")
        model = ChatGoogleGenerativeAI(model=CHAT_MODEL_NAME)
        self.agent = create_agent(
            model,
            system_prompt=SYSTEM_PROMPT,
            tools=[], 
            middleware=[RetrieveDocumentsMiddleware()],
            checkpointer=InMemorySaver()
            )
        self.config = RunnableConfig = {"configurable": {"thread_id": "1"}}

    def query(self, user_query: str) -> str:

        res = self.agent.invoke(
            {"messages": user_query},
            self.config
        )

        ai_response = res['messages'][-1].content
        
        if 'context' not in res:
            return ai_response, None
        
        retrieved_docs = res['context']
        related_news = [doc.page_content for doc in retrieved_docs]

        return ai_response, related_news