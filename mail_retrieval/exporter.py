import os

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
from pinecone import ServerlessSpec
from uuid import uuid4

INDEX_NAME = "daily-news"
EMBED_MODEL_NAME = "models/gemini-embedding-001"

class Exporter:

    def __init__(self, vector_store_key:str|None=None, llm_key:str|None=None):
        
        load_dotenv()
        api_key = vector_store_key
        google_api_key = llm_key

        if api_key is None:
            api_key = os.environ["PINECONE_API_KEY"]

        if google_api_key is None:
            google_api_key = os.environ["GOOGLE_API_KEY"]

        if api_key is None:
            raise("Couldn't find pinecone key")
        
        if google_api_key is None:
            raise("Couldn't find llm key")
        
        self.pc_store = Pinecone(api_key=api_key)
        self.create_index()
        self.index = self.pc_store.Index(name=INDEX_NAME)


        self.embedding_model = GoogleGenerativeAIEmbeddings(
            model=EMBED_MODEL_NAME, 
            task_type="RETRIEVAL_DOCUMENT",
            google_api_key=google_api_key
            )
        
        self.vector_score = PineconeVectorStore(self.index, self.embedding_model)

    def create_index(self):
        if not self.pc_store.has_index(INDEX_NAME):
            self.pc_store.create_index(
                name=INDEX_NAME,
                metric="cosine",
                dimension=3072,
                # parameters for the free tier index
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
    
    def embed_documents(self, documents:list[Document]):
        uuids = [str(uuid4()) for _ in range(len(documents))]
        self.vector_score.add_documents(documents=documents, ids=uuids, async_req=False)