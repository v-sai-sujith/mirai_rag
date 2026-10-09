import os
import shutil
import tempfile
import logging
from typing import Optional, List
from dotenv import load_dotenv

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI

try:
    from langchain.retrievers.multi_query import MultiQueryRetriever
except ImportError:
    from langchain_classic.retrievers.multi_query import MultiQueryRetriever

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# Configure logging and environment
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()
CHROMA_PERSIST_DIR = "./chroma_db"
COLLECTION_NAME = "mirai_policies"

app = FastAPI(
    title="Autonomous MirAI Student Policy Advisor API",
    description="Backend service providing policy advising for Mirai School of Technology students using RAG.",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic Schemas
class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Question asked by the student.")


class ChatResponse(BaseModel):
    answer: str = Field(..., description="Advisor response grounded strictly in the policy handbook.")


class IngestResponse(BaseModel):
    status: str
    message: str
    chunks_ingested: int


_active_model: Optional[str] = None
_active_embedding_model: Optional[str] = None


def get_active_embedding_model() -> str:
    """Find available embedding model, preferring text-embedding-004 with automatic fallback."""
    global _active_embedding_model
    if _active_embedding_model:
        return _active_embedding_model

    api_key = os.getenv("GOOGLE_API_KEY")
    candidates = ["models/text-embedding-004", "gemini-embedding-001", "models/gemini-embedding-001"]
    for model_name in candidates:
        try:
            emb = GoogleGenerativeAIEmbeddings(model=model_name, google_api_key=api_key)
            emb.embed_query("test")
            _active_embedding_model = model_name
            logger.info(f"Selected embedding model: {model_name}")
            return model_name
        except Exception as e:
            logger.warning(f"Embedding model '{model_name}' unavailable: {e}")

    _active_embedding_model = "gemini-embedding-001"
    return _active_embedding_model


def get_active_llm_model() -> str:
    """Find active generation model, preferring gemini-3.8-flash / gemini-1.5-flash with quota fallback."""
    global _active_model
    if _active_model:
        return _active_model

    api_key = os.getenv("GOOGLE_API_KEY")
    candidates = [
        "gemini-3.8-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash",
        "gemini-3.7-flash",
        "gemini-1.5-flash"
    ]

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        for model_name in candidates:
            try:
                client.models.generate_content(
                    model=model_name,
                    contents="test",
                    config={"max_output_tokens": 1}
                )
                _active_model = model_name
                logger.info(f"Selected LLM model: {model_name}")
                return model_name
            except Exception as ex:
                logger.warning(f"Model '{model_name}' unavailable ({ex}). Checking next candidate...")
    except Exception as e:
        logger.warning(f"Error checking active model: {e}")

    _active_model = "gemini-3.7-flash"
    return _active_model


def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY is not configured in the environment.")
    model_name = get_active_embedding_model()
    return GoogleGenerativeAIEmbeddings(model=model_name, google_api_key=api_key)


def get_llm() -> ChatGoogleGenerativeAI:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY is not configured in the environment.")
    model_name = get_active_llm_model()
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=0.0
    )


def clean_text_output(output) -> str:
    """Format any LLM response structure cleanly into a string."""
    if isinstance(output, str):
        return output.strip()
    if isinstance(output, list):
        extracted = []
        for item in output:
            if isinstance(item, dict) and "text" in item:
                extracted.append(item["text"])
            elif isinstance(item, str):
                extracted.append(item)
        return "".join(extracted).strip()
    return str(output).strip()


SYSTEM_PROMPT = """You are the Autonomous MirAI Student Policy Advisor for Mirai School of Technology.
Your duty is to provide strictly factual, authoritative, and direct guidance based SOLELY on the official policy handbook context provided below.

MANDATORY GUARDRAILS:
1. ZERO HALLUCINATION: Rely exclusively on the retrieved context below. Do NOT use outside training knowledge, assumptions, or external policies.
2. ABSENCE OF INFORMATION: If a topic is completely absent from the provided context, politely decline by answering: "I am sorry, but that information is not available in the official Mirai School of Technology Student Policy Handbook."
3. NEVER INVENT SANCTIONS OR MONETARY FINES: When asked about a fine or fee for a violation (such as smoking, tobacco, alcohol, or misconduct), explain what the handbook actually specifies regarding that activity (e.g., that tobacco is strictly prohibited and subject to Disciplinary Committee review/action), and explicitly state that no monetary fine is specified or defined in the handbook. Do NOT fabricate or assume any monetary amount.
4. EXACT POLICY DETAILS: Provide exact figures, percentage tiers (e.g., 75% attendance rule, 40% batch support for new clubs), submission deadlines (e.g., 7 days), and points of contact (e.g., specific Campus Managers by campus, Faculty Coordinators) as described in the handbook.

CONTEXT:
{context}

STUDENT QUESTION:
{question}

ADVISOR ANSWER:"""


@app.get("/")
@app.get("/health")
def health_check():
    vector_store_ready = os.path.exists(CHROMA_PERSIST_DIR) and len(os.listdir(CHROMA_PERSIST_DIR)) > 0
    return {
        "status": "healthy",
        "service": "Autonomous MirAI Student Policy Advisor",
        "vector_store_initialized": vector_store_ready,
        "active_model": get_active_llm_model(),
        "active_embedding_model": get_active_embedding_model()
    }


@app.post("/ingest", response_model=IngestResponse)
async def ingest_document(file: UploadFile = File(...)):
    """
    Ingest a PDF policy handbook:
    - Save upload temporarily
    - Extract text with PyPDFLoader
    - Split chunks with RecursiveCharacterTextSplitter (chunk_size=1000, chunk_overlap=200)
    - Embed and persist into ChromaDB
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only PDF documents are accepted."
        )

    try:
        # Write to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        logger.info(f"Loading document from temporary file: {tmp_file_path}")
        loader = PyPDFLoader(tmp_file_path)
        documents = loader.load()

        if not documents:
            raise HTTPException(status_code=400, detail="The uploaded PDF contained no extractable text.")

        # Semantic chunking
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = splitter.split_documents(documents)
        logger.info(f"Split {len(documents)} pages into {len(chunks)} chunks.")

        # Embedding & vectorstore persistence
        embeddings = get_embeddings()

        # Re-initialize collection in persist directory
        vectorstore = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=CHROMA_PERSIST_DIR
        )

        vectorstore.add_documents(chunks)
        logger.info(f"Successfully added {len(chunks)} chunks to ChromaDB at {CHROMA_PERSIST_DIR}.")

        # Cleanup temporary file
        os.remove(tmp_file_path)

        return IngestResponse(
            status="success",
            message=f"Successfully ingested and indexed '{file.filename}'.",
            chunks_ingested=len(chunks)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during ingestion: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to ingest document: {str(e)}")


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Answer student queries using MultiQueryRetriever and LCEL RAG chain.
    """
    if not os.path.exists(CHROMA_PERSIST_DIR) or len(os.listdir(CHROMA_PERSIST_DIR)) == 0:
        raise HTTPException(
            status_code=400,
            detail="The policy knowledge base is empty. Please upload the handbook via /ingest first."
        )

    try:
        embeddings = get_embeddings()
        vectorstore = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=CHROMA_PERSIST_DIR
        )

        base_retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
        llm = get_llm()

        # MultiQueryRetriever to bridge student casual questions with formal policy text
        retriever = MultiQueryRetriever.from_llm(
            retriever=base_retriever,
            llm=llm
        )

        prompt = ChatPromptTemplate.from_template(SYSTEM_PROMPT)

        def format_docs(docs: List) -> str:
            if not docs:
                return "No relevant policy documents found."
            return "\n\n---\n\n".join(doc.page_content for doc in docs)

        rag_chain = (
            {
                "context": retriever | format_docs,
                "question": RunnablePassthrough()
            }
            | prompt
            | llm
            | StrOutputParser()
        )

        logger.info(f"Processing question: {request.question}")
        raw_answer = rag_chain.invoke(request.question)
        final_answer = clean_text_output(raw_answer)

        return ChatResponse(answer=final_answer)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating answer: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process query: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend:app", host="0.0.0.0", port=8000, reload=True)
