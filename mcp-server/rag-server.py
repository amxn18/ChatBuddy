import json
import os
import re
import shutil
from pathlib import Path

from dotenv import load_dotenv
from fastmcp import FastMCP

from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS


load_dotenv()

mcp = FastMCP(name="RAG Server")

BASE_DIR = Path(__file__).resolve().parent
RAG_DATA_DIR = BASE_DIR / "rag_data"
RAG_DATA_DIR.mkdir(parents=True, exist_ok=True)

HF_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")

if not HF_TOKEN:
    raise RuntimeError("HF_TOKEN is missing. Add it to the mcp-server/.env file.")


embedding_model = HuggingFaceEndpointEmbeddings(
    model="sentence-transformers/all-MiniLM-L6-v2",
    task="feature-extraction",
    huggingfacehub_api_token=HF_TOKEN,
)

def get_index_dir(knowledge_base_id: str) -> Path:
    """
    Return the persistent FAISS directory for one ChatBuddy thread.
    """
    if not re.fullmatch(r"[A-Za-z0-9_-]+",knowledge_base_id):
        raise ValueError("Invalid knowledge_base_id.")

    return RAG_DATA_DIR / knowledge_base_id


def get_retriever(knowledge_base_id: str):
    """
    Load a persisted FAISS index for the requested knowledge base.
    """
    index_dir = get_index_dir(knowledge_base_id)
    if not index_dir.exists():
        return None
    index_file = index_dir / "index.faiss"

    if not index_file.exists():
        return None

    vector_store = FAISS.load_local(str(index_dir),embedding_model,allow_dangerous_deserialization=True,)

    return vector_store.as_retriever(search_type="similarity",search_kwargs={"k": 4},)


@mcp.tool()
def index_pdf(pdf_path: str,knowledge_base_id: str) -> str:
    """
    Load a PDF, split it into chunks, create embeddings through
    the Hugging Face API, and persist a FAISS index for one
    ChatBuddy conversation.
    """

    try:
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            return f"Failed: PDF not found at {pdf_path}"

        if pdf_file.suffix.lower() != ".pdf":
            return "Failed: only PDF files are supported."

        loader = PyPDFLoader(str(pdf_file))
        docs = loader.load()

        if not docs:
            return "Failed: PDF contains no readable content."


        splitter = RecursiveCharacterTextSplitter(chunk_size=1000,chunk_overlap=200)

        chunks = splitter.split_documents(docs)

        if not chunks:
            return "Failed: no text chunks were created from the PDF."
        
        vector_store = FAISS.from_documents(chunks,embedding_model)

        index_dir = get_index_dir(knowledge_base_id)

        if index_dir.exists():
            shutil.rmtree(index_dir)

        index_dir.mkdir(parents=True,exist_ok=True)

        vector_store.save_local(str(index_dir))

        metadata = {"pages": len(docs),"chunks": len(chunks),"filename": pdf_file.name}

        (index_dir / "metadata.json").write_text(
            json.dumps(metadata, indent=2),
            encoding="utf-8",
        )

        return (
            "Successfully indexed PDF.\n"
            f"Pages: {len(docs)}\n"
            f"Chunks: {len(chunks)}"
        )

    except Exception as e:
        return f"Failed to index PDF: {str(e)}"


@mcp.tool()
def rag_search(query: str, knowledge_base_id: str) -> str:
    """
    Search the persistent FAISS index associated with the
    current ChatBuddy conversation.
    """

    try:

        retriever = get_retriever(knowledge_base_id)
        if retriever is None:
            return "No PDF has been indexed for this chat."

        results = retriever.invoke(query)

        if not results:
            return "No relevant information found in the PDF."

        context = []

        for i, doc in enumerate(results, start=1):

            context.append(
                {
                    "rank": i,
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                }
            )

        return json.dumps(
            {
                "query": query,
                "results": context,
            },
            ensure_ascii=False,
            default=str,
        )

    except Exception as e:
        return f"RAG search failed: {str(e)}"


@mcp.tool()
def remove_knowledge_base(knowledge_base_id: str) -> str:
    """
    Remove the persistent FAISS index associated with a
    ChatBuddy conversation.
    """

    try:

        index_dir = get_index_dir(
            knowledge_base_id
        )

        if not index_dir.exists():
            return "No knowledge base exists for this chat."

        shutil.rmtree(index_dir)

        return "Knowledge base removed successfully."

    except Exception as e:
        return f"Failed to remove knowledge base: {str(e)}"