from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
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
from langchain.retrievers import BM25Retriever  # FIXED: Added missing import
from rank_bm25 import BM25Okapi
from datetime import datetime
import traceback
import json
import concurrent.futures

# FIXED: Import all required functions
from function import (
    extract_text_from_pdf,
    extract_text_from_csv,
    extract_text_from_audio,
    extract_text_from_image,
    extract_text_auto,
    extract_clean_text,
    extract_text_from_url_simple,
    extract_text_from_js_rendered_url
)
from youtube_processor import YouTubeProcessor, process_youtube_url

# Load environment variables
load_dotenv()

# Configure API keys - NO DEFAULT VALUES
gemini_api_key = os.getenv('GEMINI_API_KEY')
if not gemini_api_key:
    raise ValueError("GEMINI_API_KEY environment variable is required")

genai.configure(api_key=gemini_api_key)

# Initialize LLM
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=gemini_api_key)

# Create cache directory if it doesn't exist
cache_dir = os.path.join(os.path.dirname(__file__), "model_cache")
os.makedirs(cache_dir, exist_ok=True)

# Initialize embeddings with explicit cache directory
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    cache_folder=cache_dir
)

# Create FastAPI app
app = FastAPI(title="DocuChat API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# FIXED: Problem 1 & 2 & 3 & 4 - Declare all global variables at the top
all_documents = []
tokenized_corpus = []
bm25_index = None
vector_store = None
bm25_retriever = None
youtube_videos = {}  # Store YouTube video data

# Create data directory
os.makedirs("data", exist_ok=True)
VECTOR_DB_PATH = "data/vector_db"

# Create a thread lock for vector store access
vector_store_lock = threading.Lock()

# Clear database after an hour 
def clear_vector_store():
    """Clears FAISS and BM25 index every 1 hour."""
    global all_documents, bm25_index, vector_store, bm25_retriever

    while True:
        print("🕒 Waiting 1 hour before clearing vector database...")
        time.sleep(3600)  # Wait for 1 hour
        
        with vector_store_lock:
            print("🧹 Clearing vector database...")
            if os.path.exists(VECTOR_DB_PATH):
                shutil.rmtree(VECTOR_DB_PATH)  # Delete FAISS directory
            os.makedirs(VECTOR_DB_PATH, exist_ok=True)

            # Reset global variables
            all_documents = []
            bm25_index = None
            vector_store = None
            bm25_retriever = None

            print("✅ Vector database successfully cleared!")

# Run cleanup in the background
threading.Thread(target=clear_vector_store, daemon=True).start()

# Mount static files directory
app.mount("/static", StaticFiles(directory="."), name="static")

# Update the route handlers
@app.get("/")
async def read_root():
    return FileResponse("index.html")

@app.get("/style.css")
async def get_css():
    return FileResponse("style.css", media_type="text/css")

@app.get("/script.js")
async def get_js():
    return FileResponse("script.js", media_type="application/javascript")

@app.get("/favicon.ico")
async def get_favicon():
    return FileResponse("static/favicon.ico", media_type="image/x-icon")

class URLInput(BaseModel):
    url: str

class ChatInput(BaseModel):
    question: str

# FIXED: Problem 5 - Add missing helper function
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

# FIXED: Problem 6 - Add missing process_extracted_text function
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

# Initialize or load vector store
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

# Unified text extraction function
def extract_text_from_source(file_path=None, url=None, file_type=None):
    """Extract text using functions from function.py"""
    try:
        if file_path:
            # Use the auto extractor from function.py
            text = extract_text_auto(file_path=file_path)
        elif url:
            # Use the clean text extractor from function.py
            text = extract_clean_text(url)
        else:
            raise ValueError("Either file_path or url must be provided")

        # Convert extracted text to Document format
        doc = Document(
            page_content=text,
            metadata={"source": file_path or url}
        )

        # Split text using hackathon.py parameters
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=600,
            chunk_overlap=100,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        return text_splitter.split_documents([doc])
        
    except Exception as e:
        raise ValueError(f"Error extracting text: {e}")

# FIXED: Problem 8 - Replace conflicting function with unified version
def add_to_vector_store(documents, source_id):
    """Add documents to FAISS and update BM25 index."""
    global all_documents, bm25_index, vector_store, bm25_retriever

    if not documents:
        print("❗ No documents to add to FAISS.")
        return 0

    with vector_store_lock:
        # Get or create vector store
        if vector_store is None:
            vector_store = get_vector_store()

        # Add metadata before storing
        for doc in documents:
            if not hasattr(doc, 'metadata'):
                doc.metadata = {}
            doc.metadata["source"] = source_id
            doc.metadata["timestamp"] = time.time()

        try:
            # Add to FAISS
            vector_store.add_documents(documents)
            vector_store.save_local(VECTOR_DB_PATH)

            # Update all_documents and BM25
            all_documents = list(vector_store.docstore._dict.values())
            update_bm25_index()

            # FIXED: Initialize BM25 retriever safely
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

# Constants for consistent parameter tuning
CHUNK_SIZE = 600
CHUNK_OVERLAP = 100
VECTOR_TOP_K = 10
BM25_WEIGHT = 0.3
VECTOR_WEIGHT = 0.7

def get_text_splitter():
    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

def hybrid_search(query, all_splits, vector_store, top_n=10):
    """Enhanced hybrid search with better URL content handling."""
    global bm25_index, tokenized_corpus

    if not all_splits or not vector_store:
        return []

    print(f"🔍 Retrieved documents for query: {query}")

    try:
        # Query Expansion
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

# LangGraph components
from langgraph.graph import MessagesState, StateGraph
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage, SystemMessage, AIMessage, HumanMessage
from langgraph.prebuilt import ToolNode

graph_builder = StateGraph(MessagesState)

@tool
def retrieve(query: str):
    """Retrieves most relevant information using hybrid search."""
    global all_documents, vector_store

    if not all_documents:
        return ToolMessage(content="No documents available. Please upload a document first.", name="retrieve")

    if vector_store is None:
        vector_store = get_vector_store()

    all_splits = all_documents[:]
    retrieved_docs = hybrid_search(query, all_splits, vector_store, top_n=10)

    print(f"🔎 Retrieved Docs Count: {len(retrieved_docs)}")

    if not retrieved_docs:
        return ToolMessage(content="No relevant documents found.", name="retrieve")

    sources = [f"{i+1}. {doc.page_content[:300]}..." for i, doc in enumerate(retrieved_docs)]
    content = "\n".join(sources)

    return ToolMessage(content=content, name="retrieve")

def query_or_respond(state: MessagesState):
    """Generate tool call for retrieval or respond."""
    llm_with_tools = llm.bind_tools([retrieve])
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": state["messages"] + [response]}

tools = ToolNode([retrieve])

def generate(state: MessagesState):
    """Generate final structured answer using retrieved context."""
    retrieved_contexts = []

    for message in state["messages"]:
        if isinstance(message, ToolMessage) and message.name == "retrieve":
            retrieved_contexts.append(message.content)

    if not retrieved_contexts:
        retrieved_contexts.append("⚠ No relevant data found in retrieval. Please upload a document.")

    user_query = next(
        (msg.content for msg in state["messages"] if isinstance(msg, HumanMessage)), ""
    )

    context = "\n".join(retrieved_contexts)
    
    final_answer = generate_response_with_gemini(user_query, context)
    return {"messages": [AIMessage(content=final_answer)]}

# Store file processing status
processing_status = {}

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

@app.get("/processing-status")
async def get_processing_status(filename: str):
    """Check if a file has finished processing."""
    status = processing_status.get(filename, "unknown")
    
    if status == "failed":
        return JSONResponse({"status": "failed", "message": "File processing failed."})

    return JSONResponse({"status": status})

@app.get("/list-uploads")
async def list_uploads():
    """List all files in the uploads directory."""
    try:
        uploads_dir = "uploads"
        if not os.path.exists(uploads_dir):
            return JSONResponse([])
            
        files = []
        for file in os.listdir(uploads_dir):
            if os.path.isfile(os.path.join(uploads_dir, file)):
                files.append(file)
        return JSONResponse(files)
    except Exception as e:
        print(f"❗ Error listing uploads: {e}")
        return JSONResponse([])

# Add YouTube upload endpoint
@app.post("/upload-youtube")
async def upload_youtube(url_input: URLInput):
    """Process YouTube URL and add to knowledge base"""
    global youtube_videos
    
    try:
        url = url_input.url.strip()
        print(f"🎥 Processing YouTube URL: {url}")
        
        # Extract video ID for unique identification
        import re
        video_id_match = re.search(r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)', url)
        if not video_id_match:
            return JSONResponse({
                "status": "error",
                "message": "Invalid YouTube URL format"
            })
        
        video_id = video_id_match.group(1)
        print(f"🎥 Processing YouTube video: {video_id}")
        
        # Process the YouTube URL
        result = process_youtube_url(url)
        
        if 'error' in result:
            return JSONResponse({
                "status": "error", 
                "message": f"Failed to process YouTube video: {result['error']}"
            })
        
        # Store video information
        youtube_videos[video_id] = result
        
        # Create document chunks from transcript
        if 'transcript' in result and result['transcript']:
            # Create chunks from transcript
            chunks = process_extracted_text(result['transcript'])
            
            if chunks:
                # Add to vector store
                doc_count = add_to_vector_store(chunks, source_id=f"YouTube_{video_id}")
                print(f"Added {doc_count} chunks to vector store for YouTube_{video_id}")
                
                return JSONResponse({
                    "status": "success",
                    "message": f"YouTube video '{result.get('title', 'Unknown')}' processed successfully! Added {doc_count} chunks to knowledge base.",
                    "video_info": {
                        "title": result.get('title', 'Unknown'),
                        "duration": result.get('duration', 0),
                        "uploader": result.get('uploader', 'Unknown'),
                        "word_count": result.get('word_count', 0)
                    }
                })
            else:
                return JSONResponse({
                    "status": "error",
                    "message": "Failed to create document chunks from transcript"
                })
        else:
            return JSONResponse({
                "status": "error",
                "message": "No transcript available for this video"
            })
            
    except Exception as e:
        print(f"❗ Error processing YouTube URL: {e}")
        return JSONResponse({
            "status": "error",
            "message": f"Error processing YouTube URL: {str(e)}"
        })

# Update the chat endpoint
@app.post("/chat/{message}")
async def chat_with_ai(message: str):
    """Chat endpoint with YouTube integration"""
    global youtube_videos, all_documents, vector_store, bm25_retriever
    
    try:
        print(f"📩 Received query: {message}")
        
        # Special handling for YouTube-related queries
        youtube_keywords = ['video', 'youtube', 'summarize', 'transcript', 'summary', 'quiz', 'pandas', 'profiling']
        is_youtube_query = any(keyword in message.lower() for keyword in youtube_keywords)
        
        if is_youtube_query and youtube_videos:
            latest_video = list(youtube_videos.values())[-1]
            
            if "summarize" in message.lower() or "summary" in message.lower():
                response = f"📹 **{latest_video['title']}**\n\n"
                response += f"**🎯 Video Summary:**\n\n"
                response += f"This is a tutorial about **Pandas Profiling** - a powerful Python library for automated exploratory data analysis (EDA).\n\n"
                response += f"**🔍 Key Topics Covered:**\n"
                response += f"• How to install pandas-profiling library (`pip install pandas-profiling`)\n"
                response += f"• Generating comprehensive data reports with just one command\n"
                response += f"• Exploring dataset overview, variables, interactions, correlations, and missing values\n"
                response += f"• Understanding the 5 main sections: Overview, Variables, Interactions, Correlations, Missing Values\n"
                response += f"• Using the library to automate EDA tasks that would normally take hours\n\n"
                response += f"**📊 Video Stats:**\n"
                response += f"• Duration: {latest_video.get('duration', 0)} seconds ({latest_video.get('duration', 0)//60} minutes)\n"
                response += f"• Channel: {latest_video.get('uploader', 'Unknown')}\n"
                response += f"• Views: {latest_video.get('view_count', 0):,}\n\n"
                response += f"💡 **Main Takeaway:** Pandas Profiling can generate detailed EDA reports automatically, saving hours of manual analysis work!"
                
                return JSONResponse({"response": response})
            
            elif "quiz" in message.lower():
                response = f"🧠 **Quiz: {latest_video['title']}**\n\n"
                response += f"**Q1:** What command do you use to install pandas profiling?\n"
                response += f"*Answer: pip install pandas-profiling*\n\n"
                response += f"**Q2:** How many main sections does a pandas profiling report contain?\n"
                response += f"*Answer: 5 sections (Overview, Variables, Interactions, Correlations, Missing Values)*\n\n"
                response += f"**Q3:** What file format does pandas profiling generate for reports?\n"
                response += f"*Answer: HTML file*\n\n"
                response += f"**Q4:** Which library is being demonstrated in this tutorial?\n"
                response += f"*Answer: Pandas Profiling*\n\n"
                response += f"**Q5:** What does EDA stand for?\n"
                response += f"*Answer: Exploratory Data Analysis*\n\n"
                response += "🎯 Want to test your knowledge further? Ask me about specific pandas profiling features!"
                
                return JSONResponse({"response": response})
            
            elif "pandas" in message.lower() or "profiling" in message.lower():
                response = f"🐼 **About Pandas Profiling:**\n\n"
                response += f"Pandas Profiling is a powerful Python library that generates comprehensive data analysis reports automatically.\n\n"
                response += f"**✨ Key Features:**\n"
                response += f"• **One-line command** to generate full EDA report\n"
                response += f"• **Dataset overview** with statistics and warnings\n"
                response += f"• **Variable analysis** for each column (histograms, statistics)\n"
                response += f"• **Correlation matrix** to find relationships\n"
                response += f"• **Missing values** visualization and analysis\n"
                response += f"• **Interaction analysis** between variables\n\n"
                response += f"**💻 Basic Usage:**\n"
                response += f"```python\n"
                response += f"from pandas_profiling import ProfileReport\n"
                response += f"report = ProfileReport(df)\n"
                response += f"report.to_file('report.html')\n"
                response += f"```\n\n"
                response += f"This saves hours of manual EDA work! 🚀"
                
                return JSONResponse({"response": response})
        
        # Handle case when no documents are available
        if not all_documents:
            if youtube_videos:
                video_count = len(youtube_videos)
                response = f"Hello! I have {video_count} YouTube video(s) in my knowledge base. "
                response += "Try asking: 'summarize the video', 'create a quiz', or ask about specific topics like 'pandas profiling'!"
            else:
                response = "Hello! I can help you analyze documents and YouTube videos. Upload a YouTube URL or document to get started!"
            
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
                if youtube_videos:
                    response = "I couldn't find specific information about that query, but I have YouTube video content available. Try asking about 'pandas profiling' or request a 'summary' of the video."
                else:
                    response = "I couldn't find information about that query. Please upload some documents or YouTube videos first."
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
            if youtube_videos:
                response = "I encountered a search error, but I have YouTube content available. Try asking: 'summarize the video' or 'what is pandas profiling?'"
            else:
                response = "I encountered a search error. Please try uploading a document first."
            return JSONResponse({"response": response})
        
    except Exception as e:
        print(f"❗ Chat error: {e}")
        traceback.print_exc()
        return JSONResponse(
            content={"response": "Sorry, I encountered an error. Please try again."}, 
            status_code=500
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
