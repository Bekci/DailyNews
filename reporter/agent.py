import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.documents import Document
from langchain.agents.middleware import dynamic_prompt, ModelRequest, AgentMiddleware, AgentState
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langchain.messages import RemoveMessage
from langchain.agents.middleware import before_model
from langgraph.runtime import Runtime
from pinecone import Pinecone
from typing import Any
load_dotenv()

INDEX_NAME = "daily-news"
EMBED_MODEL_NAME = "gemini-embedding-001"
CHAT_MODEL_NAME = "gemini-2.5-flash-lite"

pc_store = Pinecone(api_key=os.environ.get("PINECONE_API_KEY", ""))
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

@before_model
def trim_messages(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    messages = state["messages"]

    if len(messages) <= 3:
        return None
    
    first_msg = messages[0]
    recent_messages = messages[-3:] if len(messages) % 2 == 0 else messages[-4:]
    new_messages =[first_msg] + recent_messages

    return {
        "messages": [
            RemoveMessage(id=REMOVE_ALL_MESSAGES),
            *new_messages
        ]
    }

class Ulak:
    def __init__(self):        
        model = ChatGoogleGenerativeAI(model=CHAT_MODEL_NAME)
        self.agent = create_agent(
            model, 
            tools=[], 
            middleware=[trim_messages, RetrieveDocumentsMiddleware()],
            checkpointer=InMemorySaver()
            )

    def query(self, user_query: str) -> str:

        res = self.agent.invoke(
            {"messages": [{"role": "user", "content": user_query}]},
            {"configurable": {"thread_id": 1}}
        )

        retrieved_docs = res['context']
        ai_response = res['messages'][-1].content
        related_news = "\n".join([doc.page_content for doc in retrieved_docs])

        return ai_response, related_news