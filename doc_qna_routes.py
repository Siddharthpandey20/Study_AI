from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import shutil
import re
from typing import List, Optional, Dict, Any
import threading
import requests
from bs4 import BeautifulSoup
import tempfile
import time
from dotenv import load_dotenv
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyMuPDFLoader, CSVLoader, WebBaseLoader
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.retrievers import BM25Retriever
from rank_bm25 import BM25Okapi
from datetime import datetime
import traceback
import json
import concurrent.futures

# Import extraction functions
from function_for_DOC_QNA import (
    extract_text_from_pdf,
    extract_text_from_csv,
    extract_text_from_audio,
    extract_text_from_image,
    extract_text_auto,
    extract_clean_text,
    extract_text_from_url_simple
)

# Load environment variables
load_dotenv()

# Configure API keys - NO DEFAULT VALUES
gemini_api_key = os.getenv('GEMINI_API_KEY')
if not gemini_api_key:
    raise ValueError("GEMINI_API_KEY environment variable is required")

genai.configure(api_key=gemini_api_key)

# Initialize LLM
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=gemini_api_key)

# Create cache directory
cache_dir = os.path.join(os.path.dirname(__file__), "model_cache")
os.makedirs(cache_dir, exist_ok=True)

# Initialize embeddings
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    cache_folder=cache_dir
)

# Global variables
all_documents = []
tokenized_corpus = []
bm25_index = None
vector_store = None
bm25_retriever = None

# Create data directory
os.makedirs("data", exist_ok=True)
VECTOR_DB_PATH = "data/vector_db"

# Thread lock for vector store access
vector_store_lock = threading.Lock()

# Store file processing status
processing_status = {}

class URLInput(BaseModel):
    url: str

class ChatInput(BaseModel):
    question: str

def clear_vector_store():
    """Clears FAISS and BM25 index every 1 hour."""
    global all_documents, bm25_index, vector_store, bm25_retriever

    while True:
        print("🕒 Waiting 1 hour before clearing vector database...")
        time.sleep(3600)  # Wait for 1 hour
        
        with vector_store_lock:
            print("🧹 Clearing vector database...")
            if os.path.exists(VECTOR_DB_PATH):
                shutil.rmtree(VECTOR_DB_PATH)
            os.makedirs(VECTOR_DB_PATH, exist_ok=True)

            # Reset global variables
            all_documents = []
            bm25_index = None
            vector_store = None
            bm25_retriever = None

            print("✅ Vector database successfully cleared!")

# Run cleanup in the background
threading.Thread(target=clear_vector_store, daemon=True).start()

def generate_response_with_gemini(query: str, context: str) -> str:
    """Generate response using Gemini with context"""
    try:
        prompt = f"""
        Based on the following context, answer the user's question. If the context doesn't contain relevant information, say so.
        
        Context:
        {context}
        
        Question: {query}
        
        Answer:
        """
        
        response = llm.invoke(prompt)
        return response.content if hasattr(response, 'content') else str(response)
    except Exception as e:
        print(f"Error generating response: {e}")
        return f"I encountered an error while generating a response. Context available: {len(context)} characters."

def process_extracted_text(text: str) -> List[Document]:
    """Process extracted text into document chunks"""
    try:
        if not text or not text.strip():
            return []
        
        # Create document
        doc = Document(page_content=text.strip())
        
        # Split text
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=600,
            chunk_overlap=100,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        chunks = text_splitter.split_documents([doc])
        return chunks
    except Exception as e:
        print(f"Error processing text: {e}")
        return []

def get_vector_store():
    """Load or create FAISS vector store safely."""
    global all_documents, bm25_index, vector_store

    if not os.path.exists(VECTOR_DB_PATH):
        vector_store = FAISS.from_texts(["Placeholder document"], embeddings)
        return vector_store

    try:
        vector_store = FAISS.load_local(VECTOR_DB_PATH, embeddings, allow_dangerous_deserialization=True)
        if not all_documents:
            all_documents = list(vector_store.docstore._dict.values())
        update_bm25_index()
        return vector_store
    except Exception as e:
        print(f"Error loading vector store: {e}")
        vector_store = FAISS.from_texts(["Placeholder document"], embeddings)
        return vector_store

def update_bm25_index():
    """Update the BM25 index with FAISS documents."""
    global bm25_index, tokenized_corpus, all_documents

    if not all_documents:
        return

    try:
        tokenized_corpus = [doc.page_content.lower().split() for doc in all_documents]
        bm25_index = BM25Okapi(tokenized_corpus)
        print(f"✅ BM25 index updated with {len(all_documents)} documents")
    except Exception as e:
        print(f"Error updating BM25 index: {e}")

def extract_text_from_source(file_path=None, url=None):
    """Extract text using functions from function_for_DOC_QNA.py"""
    try:
        if file_path:
            text = extract_text_auto(file_path=file_path)
        elif url:
            text = extract_clean_text(url)
        else:
            raise ValueError("Either file_path or url must be provided")

        doc = Document(
            page_content=text,
            metadata={"source": file_path or url}
        )

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=600,
            chunk_overlap=100,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        return text_splitter.split_documents([doc])
        
    except Exception as e:
        raise ValueError(f"Error extracting text: {e}")

def add_to_vector_store(documents, source_id):
    """Add documents to FAISS and update BM25 index."""
    global all_documents, bm25_index, vector_store, bm25_retriever

    if not documents:
        print("❗ No documents to add to FAISS.")
        return 0

    with vector_store_lock:
        if vector_store is None:
            vector_store = get_vector_store()

        for doc in documents:
            if not hasattr(doc, 'metadata'):
                doc.metadata = {}
            doc.metadata["source"] = source_id
            doc.metadata["timestamp"] = time.time()

        try:
            vector_store.add_documents(documents)
            vector_store.save_local(VECTOR_DB_PATH)

            all_documents = list(vector_store.docstore._dict.values())
            update_bm25_index()

            try:
                if all_documents:
                    bm25_retriever = BM25Retriever.from_documents(all_documents)
                    bm25_retriever.k = 5
                    print(f"✅ BM25 retriever initialized with {len(all_documents)} documents")
            except Exception as e:
                print(f"⚠️ BM25 retriever initialization failed: {e}")
                bm25_retriever = None

            print(f"✅ {len(documents)} documents added to FAISS.")
            print(f"📂 FAISS now contains {len(all_documents)} documents.")

            return len(documents)
            
        except Exception as e:
            print(f"Error adding documents to vector store: {e}")
            return 0

def hybrid_search(query, all_splits, vector_store, top_n=10):
    """Enhanced hybrid search."""
    global bm25_index, tokenized_corpus

    if not all_splits or not vector_store:
        return []

    print(f"🔍 Retrieved documents for query: {query}")

    try:
        expanded_query = llm.invoke(f"Expand this search query while maintaining its core meaning: '{query}'")
        expanded_query = expanded_query.content if hasattr(expanded_query, "content") else str(expanded_query)

        results = []
        
        # Get vector results
        try:
            vector_results = vector_store.similarity_search_with_score(expanded_query, k=top_n)
            results.extend([doc for doc, score in vector_results])
        except Exception as e:
            print(f"Vector search failed: {e}")

        # Get BM25 results if available
        if bm25_index and tokenized_corpus:
            try:
                query_tokens = expanded_query.lower().split()
                scores = bm25_index.get_scores(query_tokens)
                top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_n]
                bm25_results = [all_splits[i] for i in top_indices if i < len(all_splits)]
                results.extend(bm25_results)
            except Exception as e:
                print(f"BM25 search failed: {e}")

        print(f"📊 Found {len(results)} relevant documents")
        return results[:top_n]
        
    except Exception as e:
        print(f"Hybrid search error: {e}")
        return []

def process_file(file_path, filename):
    """Extract text and update vector store in a background thread."""
    global processing_status, all_documents
    try:
        print(f"📂 Processing file: {filename}")
        processing_status[filename] = "processing"

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(extract_text_from_source, file_path=file_path)
            try:
                docs = future.result(timeout=60)
            except concurrent.futures.TimeoutError:
                print(f"❗ Timeout while extracting text from {filename}")
                processing_status[filename] = "failed"
                return

        if not docs:
            print(f"❗ No valid text extracted from {filename}")
            processing_status[filename] = "failed"
            return
        
        processed_docs = process_extracted_text(docs[0].page_content)
        
        if not processed_docs:
            print(f"❗ No valid content chunks were generated from {filename}")
            processing_status[filename] = "failed"
            return
        
        doc_count = add_to_vector_store(processed_docs, source_id=filename)
        print(f"✅ File {filename} processed successfully. {doc_count} documents added.")

        processing_status[filename] = "completed"

    except Exception as e:
        print(f"❗ Error processing {filename}: {e}")
        processing_status[filename] = "failed"

# Document Q&A routes
def create_doc_qna_routes(app: FastAPI):
    """Add document Q&A routes to the main FastAPI app"""
    
    @app.get("/doc-chat", response_class=HTMLResponse)
    async def get_doc_chat_page():
        """Serve the document chat page"""
        try:
            if os.path.exists("templates/doc-chat.html"):
                with open("templates/doc-chat.html", "r", encoding="utf-8") as f:
                    return HTMLResponse(content=f.read())
            else:
                raise HTTPException(status_code=404, detail="Chat page not found")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/upload")
    async def upload_file(file: UploadFile = File(...)):
        try:
            os.makedirs("uploads", exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = f"uploads/{timestamp}_{file.filename}"

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            print(f"📂 File {file.filename} saved. Now extracting text...")
            processing_status[file.filename] = "processing"

            threading.Thread(target=process_file, args=(file_path, file.filename), daemon=True).start()

            return JSONResponse({
                "status": "success",
                "message": "File uploaded successfully and is being processed.",
                "filename": file.filename
            })

        except Exception as e:
            print(f"❗ Error processing file {file.filename}: {e}")
            raise HTTPException(500, detail=str(e))

    @app.post("/upload-url")
    async def upload_url(url_input: URLInput):
        """Process URL and add to knowledge base"""
        try:
            url = url_input.url.strip()
            print(f"🌐 Processing URL: {url}")
            
            # Process the URL
            docs = extract_text_from_source(url=url)
            
            if not docs:
                return JSONResponse({
                    "status": "error",
                    "message": "No content could be extracted from the URL"
                })
            
            processed_docs = process_extracted_text(docs[0].page_content)
            
            if processed_docs:
                doc_count = add_to_vector_store(processed_docs, source_id=url)
                print(f"Added {doc_count} chunks to vector store for {url}")
                
                return JSONResponse({
                    "status": "success",
                    "message": f"URL content processed successfully! Added {doc_count} chunks to knowledge base.",
                    "url": url
                })
            else:
                return JSONResponse({
                    "status": "error",
                    "message": "Failed to create document chunks from URL content"
                })
                
        except Exception as e:
            print(f"❗ Error processing URL: {e}")
            return JSONResponse({
                "status": "error",
                "message": f"Error processing URL: {str(e)}"
            })

    @app.get("/processing-status")
    async def get_processing_status(filename: str):
        """Check if a file has finished processing."""
        status = processing_status.get(filename, "unknown")
        
        if status == "failed":
            return JSONResponse({"status": "failed", "message": "File processing failed."})

        return JSONResponse({"status": status})

    @app.post("/chat/{message}")
    async def chat_with_ai(message: str):
        """Chat endpoint for document Q&A"""
        global all_documents, vector_store
        
        try:
            print(f"📩 Received query: {message}")
            
            # Handle case when no documents are available
            if not all_documents:
                response = "Hello! I can help you analyze documents, images, audio files, and web content. Upload some files or add URLs to get started!"
                return JSONResponse({"response": response})
            
            # Regular chat with document search
            try:
                print("✅ Running hybrid search for query:", message)
                
                if vector_store is None:
                    vector_store = get_vector_store()
                
                # Perform hybrid search
                results = hybrid_search(message, all_documents, vector_store, top_n=5)
                
                if not results:
                    print("⚠️ No search results found")
                    response = "I couldn't find specific information about that query in your uploaded documents. Try uploading more relevant content or rephrasing your question."
                    return JSONResponse({"response": response})
                
                print(f"🔍 Retrieved {len(results)} total documents for query: {message}")
                
                # Create context from results
                context = ""
                for i, doc in enumerate(results[:3]):
                    if hasattr(doc, 'page_content'):
                        context += f"Document {i+1}:\n{doc.page_content}\n\n"
                    else:
                        context += f"Document {i+1}:\n{str(doc)}\n\n"
                
                # Generate response using Gemini
                response_text = generate_response_with_gemini(message, context)
                return JSONResponse({"response": response_text})
                    
            except Exception as e:
                print(f"❌ Search error: {e}")
                response = "I encountered a search error. Please try uploading a document first or try a different question."
                return JSONResponse({"response": response})
            
        except Exception as e:
            print(f"❗ Chat error: {e}")
            traceback.print_exc()
            return JSONResponse(
                content={"response": "Sorry, I encountered an error. Please try again."}, 
                status_code=500
            )

    return app
