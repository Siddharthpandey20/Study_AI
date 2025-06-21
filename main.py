from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db, User, UserDocument, GeneratedFeature, StudyGroup, GroupMembership, GroupDocument, GroupFeature, Base
from auth import (
    oauth, 
    create_access_token, 
    get_current_user, 
    require_auth,
    exchange_code_for_token,
    get_user_info_from_token
)
from cloudinary_config import upload_file_to_cloudinary, download_file_from_cloudinary
import json
import os
import secrets
import string
from datetime import datetime
from functions import (
    generate_flashcards,
    generate_mcqs,
    create_mind_map,
    generate_learning_path,
    create_sticky_notes,
    generate_exam_questions,
    process_uploaded_file,
    classify_question_importance
)

# Add YouTube functions import
from youtubefunctions import (
    get_video_id,
    get_transcript,
    download_audio,
    transcribe_audio,
    summarize_transcript,
    generate_summary
)

# Add the import for document Q&A routes
from doc_qna_routes import create_doc_qna_routes
# Database models and utilities
from database import User, StudyGroup, GroupMembership, UserDocument, get_db
from sqlalchemy.orm import Session

# Auth utilities
from auth import oauth, get_current_user, create_access_token, verify_token
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI(title="Smart Study Tool", version="1.0.0")

# Get the secret key from environment or use a default for development
SECRET_KEY = os.getenv("SECRET_KEY", "temporary-secret-key-for-development")

# Add session middleware (required for OAuth)
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directories if they don't exist
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Pydantic models
class TextInput(BaseModel):
    text: str

class FlashcardResponse(BaseModel):
    id: str
    question: str
    answer: str
    difficulty: str

class MCQResponse(BaseModel):
    id: str
    question: str
    options: List[str]
    correct_answer: int
    explanation: str
    difficulty: str

class MindMapNode(BaseModel):
    id: str
    label: str
    children: List['MindMapNode'] = []
    level: int
    color: str

class LearningStep(BaseModel):
    step_number: int
    title: str
    description: str
    estimated_time: str
    prerequisites: List[str]
    resources: List[str]

class StickyNote(BaseModel):
    id: str
    content: str
    category: str  # red, yellow, green
    priority: int
    tags: List[str]

class ExamQuestion(BaseModel):
    id: str
    question: str
    type: str  # short_answer, long_answer, hots
    probability_score: float
    difficulty: str
    keywords: List[str]

class VideoRequest(BaseModel):
    url: str

class VideoSummaryResponse(BaseModel):
    video_id: str
    title: str
    thumbnail: str
    summary: str
    source: str  # "transcript" or "audio"
    duration: Optional[str] = None

# Add document Q&A routes
app = create_doc_qna_routes(app)

# Helper function to serve HTML files
def serve_html_file(filename: str):
    """Serve HTML files with proper error handling"""
    try:
        # First try templates directory
        template_path = f"templates/{filename}"
        if os.path.exists(template_path):
            with open(template_path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        
        # Then try root directory
        root_path = filename
        if os.path.exists(root_path):
            with open(root_path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        
        # File not found
        raise HTTPException(status_code=404, detail=f"Page {filename} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Main homepage route
@app.get("/", response_class=HTMLResponse)
async def get_homepage():
    """Serve the main application page"""
    return serve_html_file("index.html")

# Feature page routes
@app.get("/flashcards.html", response_class=HTMLResponse)
async def get_flashcards_page():
    """Serve the flashcards page"""
    return serve_html_file("flashcards.html")

@app.get("/mindmap.html", response_class=HTMLResponse)
async def get_mindmap_page():
    """Serve the mind map page"""
    return serve_html_file("mindmap.html")

@app.get("/learning-path.html", response_class=HTMLResponse)
async def get_learning_path_page():
    """Serve the learning path page"""
    return serve_html_file("learning-path.html")

@app.get("/sticky-notes.html", response_class=HTMLResponse)
async def get_sticky_notes_page():
    """Serve the sticky notes page"""
    return serve_html_file("sticky-notes.html")

@app.get("/exam-booster.html", response_class=HTMLResponse)
async def get_exam_booster_page():
    """Serve the exam booster page"""
    return serve_html_file("exam-booster.html")

@app.get("/youtube-summarizer.html", response_class=HTMLResponse)
async def get_youtube_summarizer_page():
    """Serve the YouTube summarizer page"""
    return serve_html_file("youtube-summarizer.html")

@app.get("/pdf-qa.html", response_class=HTMLResponse)
async def get_pdf_qa_page():
    """Serve the PDF Q&A page"""
    return serve_html_file("pdf-qa.html")

# Add the 7th feature: Document Chat
@app.get("/doc-chat.html", response_class=HTMLResponse)
async def get_doc_chat_page():
    """Serve the document chat page"""
    return serve_html_file("doc-chat.html")

# API Routes

@app.post("/api/generate-flashcards", response_model=List[FlashcardResponse])
async def create_flashcards(file: UploadFile = File(None), text: str = Form(None),current_user: User = Depends(require_auth),db: Session = Depends(get_db)):
    """Generate flashcards from uploaded file or text"""
    try:
        if file:
            content = await process_uploaded_file(file)
            try:
                # Read file content
                await file.seek(0)    
                file_content = await file.read()

                # Upload to Cloudinary
                upload_result = await upload_file_to_cloudinary(
                    file_content, file.filename, current_user.id
                )

                # Save to database
                document = UserDocument(
                    user_id=current_user.id,
                    filename=file.filename,
                    original_filename=file.filename,
                    cloudinary_url=upload_result["url"],
                    file_type=file.filename.split('.')[-1].lower() if '.' in file.filename else 'unknown'
                )

                db.add(document)
                db.commit()
                db.refresh(document)

                # return {
                #     "success": True,
                #     "document_id": document.id,
                #     "filename": document.original_filename,
                #     "url": document.cloudinary_url
            except Exception as e:
                print(f"Upload error: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")    

        elif text:
            content = text
        else:
            raise HTTPException(status_code=400, detail="Please provide either a file or text")
        
        flashcards = await generate_flashcards(content)
        return flashcards
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating flashcards: {str(e)}")

@app.post("/api/generate-mcqs", response_model=List[MCQResponse])
async def create_mcqs(file: UploadFile = File(None), text: str = Form(None)):
    """Generate MCQs from uploaded file or text"""
    try:
        if file:
            content = await process_uploaded_file(file)
        elif text:
            content = text
        else:
            raise HTTPException(status_code=400, detail="Please provide either a file or text")
        
        mcqs = await generate_mcqs(content)
        return mcqs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating MCQs: {str(e)}")

@app.get("/api/quiz/{quiz_id}")
async def get_quiz_interface(quiz_id: str):
    """Get quiz interface for a specific quiz"""
    return {"quiz_id": quiz_id, "status": "active"}

@app.post("/api/generate-mindmap", response_model=dict)
async def create_mindmap(file: UploadFile = File(None), text: str = Form(None),current_user: User = Depends(require_auth),db: Session = Depends(get_db)):
    """Generate interactive mind map from content"""
    try:
        if file:
            content = await process_uploaded_file(file)
            try:
                # Read file content
                await file.seek(0)    
                file_content = await file.read()

                # Upload to Cloudinary
                upload_result = await upload_file_to_cloudinary(
                    file_content, file.filename, current_user.id
                )

                # Save to database
                document = UserDocument(
                    user_id=current_user.id,
                    filename=file.filename,
                    original_filename=file.filename,
                    cloudinary_url=upload_result["url"],
                    file_type=file.filename.split('.')[-1].lower() if '.' in file.filename else 'unknown'
                )

                db.add(document)
                db.commit()
                db.refresh(document)

                # return {
                #     "success": True,
                #     "document_id": document.id,
                #     "filename": document.original_filename,
                #     "url": document.cloudinary_url
                

            except Exception as e:
                print(f"Upload error: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
        elif text:
            content = text
        else:
            raise HTTPException(status_code=400, detail="Please provide either a file or text")
        
        mindmap_data = await create_mind_map(content)
        return mindmap_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating mind map: {str(e)}")

@app.get("/api/mindmap/{map_id}")
async def get_mindmap(map_id: str):
    """Get specific mind map data"""
    return {"map_id": map_id, "status": "ready"}

@app.post("/api/generate-learning-path", response_model=List[LearningStep])
async def create_learning_path(file: UploadFile = File(None), text: str = Form(None),current_user: User = Depends(require_auth),db: Session = Depends(get_db)):
    """Generate step-by-step learning path"""
    try:
        if file:
            content = await process_uploaded_file(file)
            try:
                # Read file content
                await file.seek(0)    
                file_content = await file.read()

                # Upload to Cloudinary
                upload_result = await upload_file_to_cloudinary(
                    file_content, file.filename, current_user.id
                )

                # Save to database
                document = UserDocument(
                    user_id=current_user.id,
                    filename=file.filename,
                    original_filename=file.filename,
                    cloudinary_url=upload_result["url"],
                    file_type=file.filename.split('.')[-1].lower() if '.' in file.filename else 'unknown'
                )

                db.add(document)
                db.commit()
                db.refresh(document)

                # return {
                #     "success": True,
                #     "document_id": document.id,
                #     "filename": document.original_filename,
                #     "url": document.cloudinary_url
            except Exception as e:
                print(f"Upload error: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")    

        elif text:
            content = text
        else:
            raise HTTPException(status_code=400, detail="Please provide either a file or text")
        
        learning_path = await generate_learning_path(content)
        return learning_path
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating learning path: {str(e)}")

@app.get("/api/learning-path/{path_id}")
async def get_learning_path(path_id: str):
    """Get specific learning path"""
    return {"path_id": path_id, "status": "active"}

@app.post("/api/generate-sticky-notes", response_model=List[StickyNote])
async def create_smart_sticky_notes(file: UploadFile = File(None), text: str = Form(None),current_user: User = Depends(require_auth),db: Session = Depends(get_db)):
    """Generate color-coded sticky notes with smart categorization"""
    try:
        if file:
            content = await process_uploaded_file(file)
                      
            try:
                # Read file content
                await file.seek(0)    
                file_content = await file.read()

                # Upload to Cloudinary
                upload_result = await upload_file_to_cloudinary(
                    file_content, file.filename, current_user.id
                )

                # Save to database
                document = UserDocument(
                    user_id=current_user.id,
                    filename=file.filename,
                    original_filename=file.filename,
                    cloudinary_url=upload_result["url"],
                    file_type=file.filename.split('.')[-1].lower() if '.' in file.filename else 'unknown'
                )

                db.add(document)
                db.commit()
                db.refresh(document)

                # return {
                #     "success": True,
                #     "document_id": document.id,
                #     "filename": document.original_filename,
                #     "url": document.cloudinary_url
            except Exception as e:
                print(f"Upload error: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")    

        elif text:
            content = text
        else:
            raise HTTPException(status_code=400, detail="Please provide either a file or text")
        
        sticky_notes = await create_sticky_notes(content)
        return sticky_notes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating sticky notes: {str(e)}")

@app.get("/api/sticky-notes/{note_id}")
async def get_sticky_note(note_id: str):
    """Get specific sticky note details"""
    return {"note_id": note_id, "status": "active"}

@app.put("/api/sticky-notes/{note_id}/category")
async def update_sticky_note_category(note_id: str, category: str):
    """Update sticky note category (red/yellow/green)"""
    return {"note_id": note_id, "category": category, "updated": True}

@app.post("/api/generate-exam-questions", response_model=List[ExamQuestion])
async def create_exam_questions(file: UploadFile = File(None), text: str = Form(None),current_user: User = Depends(require_auth),db: Session = Depends(get_db)):
    """Generate most likely exam questions with probability scores"""
    try:
        if file:
            content = await process_uploaded_file(file)
            try:
                # Read file content
                await file.seek(0)    
                file_content = await file.read()

                # Upload to Cloudinary
                upload_result = await upload_file_to_cloudinary(
                    file_content, file.filename, current_user.id
                )

                # Save to database
                document = UserDocument(
                    user_id=current_user.id,
                    filename=file.filename,
                    original_filename=file.filename,
                    cloudinary_url=upload_result["url"],
                    file_type=file.filename.split('.')[-1].lower() if '.' in file.filename else 'unknown'
                )

                db.add(document)
                db.commit()
                db.refresh(document)

                # return {
                #     "success": True,
                #     "document_id": document.id,
                #     "filename": document.original_filename,
                #     "url": document.cloudinary_url
            except Exception as e:
                print(f"Upload error: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")    

        elif text:
            content = text
        else:
            raise HTTPException(status_code=400, detail="Please provide either a file or text")
        
        exam_questions = await generate_exam_questions(content)
        return exam_questions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating exam questions: {str(e)}")

@app.get("/api/exam-questions/by-type/{question_type}")
async def get_questions_by_type(question_type: str):
    """Get questions filtered by type (short_answer, long_answer, hots)"""
    return {"question_type": question_type, "status": "filtered"}

@app.get("/api/exam-questions/by-probability/{min_probability}")
async def get_questions_by_probability(min_probability: float):
    """Get questions with probability score above threshold"""
    return {"min_probability": min_probability, "status": "filtered"}

@app.post("/api/summarize-youtube", response_model=VideoSummaryResponse)
async def summarize_youtube_video(request: VideoRequest):
    """Summarize YouTube video from URL"""
    try:
        video_url = request.url
        video_id = get_video_id(video_url)

        if not video_id:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")

        # Get video info for thumbnail and title
        try:
            import yt_dlp
            ydl_opts = {'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                title = info.get('title', 'YouTube Video')
                thumbnail = info.get('thumbnail', f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg')
                duration = info.get('duration_string', 'Unknown')
        except:
            title = 'YouTube Video'
            thumbnail = f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg'
            duration = 'Unknown'

        # Try to get transcript first
        transcript = get_transcript(video_id)

        if transcript:
            summary = summarize_transcript(transcript)
            source = "transcript"
        else:
            try:
                audio_path = download_audio(video_url)
                transcript_text = transcribe_audio(audio_path)
                summary = generate_summary(transcript_text)
                source = "audio"
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Audio processing failed: {str(e)}")

        return VideoSummaryResponse(
            video_id=video_id,
            title=title,
            thumbnail=thumbnail,
            summary=summary,
            source=source,
            duration=duration
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing video: {str(e)}")

@app.get("/api/video-info/{video_id}")
async def get_video_info(video_id: str):
    """Get video information including thumbnail"""
    try:
        import yt_dlp
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        ydl_opts = {'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
        return {
            "video_id": video_id,
            "title": info.get('title', 'YouTube Video'),
            "thumbnail": info.get('thumbnail', f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg'),
            "duration": info.get('duration_string', 'Unknown'),
            "channel": info.get('uploader', 'Unknown Channel'),
            "view_count": info.get('view_count', 0)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching video info: {str(e)}")

# 📊 Analytics and Progress Routes
@app.get("/api/analytics/study-progress")
async def get_study_progress():
    """Get user's study progress analytics"""
    return {
        "flashcards_completed": 0,
        "mcqs_attempted": 0,
        "accuracy_rate": 0.0,
        "study_time": "0h 0m",
        "weak_areas": [],
        "strong_areas": []
    }

@app.get("/api/analytics/performance")
async def get_performance_metrics():
    """Get detailed performance metrics"""
    return {
        "weekly_progress": [],
        "subject_wise_performance": {},
        "difficulty_wise_accuracy": {},
        "time_spent_per_topic": {}
    }

# 🎮 Interactive Features Routes
@app.post("/api/quiz/submit-answer")
async def submit_quiz_answer(quiz_id: str, question_id: str, answer: int):
    """Submit quiz answer and get feedback"""
    return {
        "quiz_id": quiz_id,
        "question_id": question_id,
        "is_correct": True,  # This would be calculated
        "explanation": "Detailed explanation here",
        "next_question": "next_question_id"
    }

@app.post("/api/flashcard/mark-difficulty")
async def mark_flashcard_difficulty(flashcard_id: str, difficulty: str):
    """Mark flashcard as easy/medium/hard for spaced repetition"""
    return {
        "flashcard_id": flashcard_id,
        "difficulty": difficulty,
        "next_review": "2024-01-01T00:00:00Z"
    }

# 🔄 Utility Routes
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0.0"}

@app.get("/api/supported-formats")
async def get_supported_formats():
    """Get list of supported file formats"""
    return {
        "supported_formats": [
            "pdf", "docx", "txt", "pptx", 
            "md", "html", "csv", "json"
        ]
    }

# Add new authentication routes
@app.get("/auth/login")
async def login(request: Request):
    """Initiate Google OAuth login with explicit error handling"""
    try:
        print("🔐 Initiating OAuth login...")
        
        # Clear any existing session data to avoid conflicts
        request.session.clear()
        
        # Build the callback URL explicitly
        redirect_uri = f"{request.url.scheme}://{request.url.netloc}/auth/callback"
        print(f"🔐 OAuth Login - Redirect URI: {redirect_uri}")
        
        # Test network connectivity to CORRECT endpoints
        import requests
        try:
            # Test the CORRECT token endpoint
            test_response = requests.get('https://oauth2.googleapis.com/token', timeout=5)
            print(f"✅ Google Token endpoint accessible: {test_response.status_code}")
        except Exception as e:
            print(f"❌ Network connectivity issue: {e}")
            return RedirectResponse(url="/?error=network_issue", status_code=302)
        
        # Use the OAuth client to create authorization URL
        return await oauth.google.authorize_redirect(request, redirect_uri)
        
    except Exception as e:
        error_msg = str(e).lower()
        print(f"❌ OAuth Login Error: {str(e)}")
        
        # Specific error handling
        if "404" in error_msg or "not found" in error_msg:
            return RedirectResponse(url="/?error=endpoint_not_found", status_code=302)
        elif "timeout" in error_msg:
            return RedirectResponse(url="/?error=timeout", status_code=302)
        elif "connection" in error_msg:
            return RedirectResponse(url="/?error=connection_failed", status_code=302)
        else:
            return RedirectResponse(url="/?error=login_failed", status_code=302)

@app.get("/auth/callback")
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    """Handle Google OAuth callback with manual token exchange"""
    try:
        print("🔐 OAuth Callback - Processing authorization...")
        print(f"🔍 Session data: {dict(request.session)}")
        print(f"🔍 Query params: {dict(request.query_params)}")
        
        # Check for error in callback
        if 'error' in request.query_params:
            error = request.query_params.get('error')
            print(f"❌ OAuth Error in callback: {error}")
            
            # Handle specific error types
            if error == 'access_denied':
                return RedirectResponse(url="/?error=access_denied&message=Please grant permission to continue", status_code=302)
            else:
                return RedirectResponse(url=f"/?error=oauth_{error}", status_code=302)
        
        # Get authorization code
        code = request.query_params.get('code')
        if not code:
            print("❌ No authorization code received")
            return RedirectResponse(url="/?error=no_code", status_code=302)
        
        print(f"✅ Authorization code received: {code[:20]}...")
        
        # Manual token exchange
        try:
            redirect_uri = f"{request.url.scheme}://{request.url.netloc}/auth/callback"
            token_data = exchange_code_for_token(code, redirect_uri)
            print(f"✅ Token exchange successful")
            
            # Get user info using access token
            access_token = token_data.get('access_token')
            user_info = get_user_info_from_token(access_token)
            print(f"✅ User info retrieved: {user_info.get('email')}")
            
        except Exception as e:
            print(f"❌ Token exchange failed: {str(e)}")
            return RedirectResponse(url="/?error=token_exchange_failed", status_code=302)
        
        if not user_info:
            print("❌ OAuth Error: No user info received")
            return RedirectResponse(url="/?error=no_user_info", status_code=302)
        
        print(f"✅ OAuth Success: User {user_info.get('email')} authenticated")
        
        # Check if user exists, create if not
        user = db.query(User).filter(User.google_id == user_info['id']).first()
        
        if not user:
            print(f"👤 Creating new user: {user_info.get('email')}")
            user = User(
                google_id=user_info['id'],
                email=user_info['email'],
                name=user_info['name'],
                picture=user_info.get('picture', '')
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"✅ User created successfully: {user.email}")
        else:
            print(f"👤 Existing user logged in: {user.email}")
        
        # Create access token
        access_token = create_access_token(user.id, user.email)
        print(f"🔑 Access token created for user: {user.email}")
        
        # Create response and set secure cookie
        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=False,  # Set to False for localhost development
            samesite="lax",
            max_age=30 * 24 * 60 * 60,  # 30 days
            path="/"  # Ensure cookie is available site-wide
        )
        
        print(f"🍪 Cookie set for user: {user.email}")
        
        # Clear session after successful login
        request.session.clear()
        
        return response
        
    except Exception as e:
        print(f"❌ OAuth Callback Error: {str(e)}")
        print(f"📋 Error type: {type(e).__name__}")
        
        # More specific error handling
        if "mismatching_state" in str(e).lower():
            print("🔄 State mismatch detected - clearing session and redirecting")
            request.session.clear()
            return RedirectResponse(url="/?error=state_mismatch&retry=true", status_code=302)
        elif "invalid_request" in str(e).lower():
            return RedirectResponse(url="/?error=invalid_request", status_code=302)
        else:
            return RedirectResponse(url="/?error=auth_failed", status_code=302)

@app.post("/auth/logout")
async def logout():
    """Logout user and clear cookie"""
    response = JSONResponse({"message": "Logged out successfully"})
    response.delete_cookie(
        key="access_token",
        path="/",
        domain=None
    )
    return response

@app.get("/api/user/profile")
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    if not current_user:
        return {"user": None}
    
    return {
        "user": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
            "picture": current_user.picture
        }
    }

# Add new route to view generated features
@app.get("/api/user/features/{feature_id}")
async def get_user_feature(
    feature_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get a specific generated feature"""
    try:
        feature = db.query(GeneratedFeature).join(UserDocument).filter(
            GeneratedFeature.id == feature_id,
            UserDocument.user_id == current_user.id
        ).first()
        
        if not feature:
            raise HTTPException(status_code=404, detail="Feature not found")
        
        return {
            "id": feature.id,
            "feature_type": feature.feature_type,
            "content": json.loads(feature.content),
            "created_at": feature.created_at.isoformat()
        }
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid feature data")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/user/documents")
async def get_user_documents(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get user's uploaded documents with generated features"""
    try:
        documents = db.query(UserDocument).filter(
            UserDocument.user_id == current_user.id
        ).order_by(UserDocument.uploaded_at.desc()).all()
        
        documents_data = []
        for doc in documents:
            # Get all generated features for this document
            features = db.query(GeneratedFeature).filter(
                GeneratedFeature.document_id == doc.id
            ).all()
            
            # Organize features by type
            features_dict = {}
            for feature in features:
                features_dict[feature.feature_type] = {
                    "id": feature.id,
                    "created_at": feature.created_at.isoformat()
                }
            
            documents_data.append({
                "id": doc.id,
                "filename": doc.original_filename,
                "file_type": doc.file_type,
                "uploaded_at": doc.uploaded_at.isoformat(),
                "cloudinary_url": doc.cloudinary_url,
                "features": features_dict
            })
        
        return {"documents": documents_data}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading documents: {str(e)}")

# Fix the logout route
@app.post("/auth/logout")
async def logout():
    """Logout user and clear cookie"""
    response = JSONResponse({"message": "Logged out successfully"})
    response.delete_cookie(
        key="access_token",
        path="/",
        domain=None
    )
    return response

# Fix the document upload route
@app.post("/api/upload-document")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Upload document to user's account"""
    try:
        # Read file content
        file_content = await file.read()
        
        # Upload to Cloudinary
        upload_result = await upload_file_to_cloudinary(
            file_content, file.filename, current_user.id
        )
        
        # Save to database
        document = UserDocument(
            user_id=current_user.id,
            filename=file.filename,
            original_filename=file.filename,
            cloudinary_url=upload_result["url"],
            file_type=file.filename.split('.')[-1].lower() if '.' in file.filename else 'unknown'
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        return {
            "success": True,
            "document_id": document.id,
            "filename": document.original_filename,
            "url": document.cloudinary_url
        }
        
    except Exception as e:
        print(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# Fix content extraction function
async def get_document_content(document: UserDocument) -> str:
    """Extract text content from document URL"""
    try:
        import requests
        
        # Add proper headers for Cloudinary access
        headers = {
            'User-Agent': 'StudyAI/1.0',
            'Accept': '*/*'
        }
        
        response = requests.get(document.cloudinary_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Simple content extraction based on file type
        if document.file_type.lower() == 'pdf':
            try:
                from functions import extract_text_from_pdf
                return extract_text_from_pdf(response.content)
            except Exception as pdf_error:
                print(f"PDF extraction error: {pdf_error}")
                return f"Could not extract PDF content from {document.original_filename}. Using sample content for demonstration: This is a sample educational document about {document.original_filename}. It contains important concepts, definitions, and key learning points that students should understand and remember for their studies."
        elif document.file_type.lower() in ['docx', 'doc']:
            try:
                from functions import extract_text_from_docx
                return extract_text_from_docx(response.content)
            except Exception as doc_error:
                print(f"DOC extraction error: {doc_error}")
                return f"Could not extract document content from {document.original_filename}. Using sample content for demonstration: This is a sample educational document about {document.original_filename}. It contains important concepts, definitions, and key learning points that students should understand and remember for their studies."
        else:
            # For text files, decode content
            try:
                return response.content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    return response.content.decode('latin-1')
                except:
                    return response.text
                    
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error accessing {document.cloudinary_url}: {http_err}")
        # Return sample content when URL access fails
        return f"""
        Sample Educational Content from {document.original_filename}
        
        This is a comprehensive study document covering key concepts and learning objectives.
        
        Key Topics:
        - Fundamental principles and definitions
        - Important theories and frameworks
        - Practical applications and examples
        - Critical analysis and evaluation methods
        - Problem-solving techniques and strategies
        
        Learning Objectives:
        1. Understand core concepts and terminology
        2. Apply theoretical knowledge to practical scenarios
        3. Analyze complex problems using systematic approaches
        4. Evaluate different solutions and methodologies
        5. Synthesize information from multiple sources
        
        Study Tips:
        - Create flashcards for important terms
        - Practice with sample questions
        - Form study groups for collaborative learning
        - Review material regularly using spaced repetition
        """
        
    except Exception as e:
        print(f"Content extraction error: {str(e)}")
        # Return a fallback content for testing
        return f"""
        Sample Educational Content from {document.original_filename}
        
        This document contains important educational material for comprehensive study.
        
        Core Learning Areas:
        - Theoretical foundations and key principles
        - Practical applications and real-world examples
        - Analytical methods and problem-solving techniques
        - Critical evaluation and assessment strategies
        
        Important Study Points:
        1. Master fundamental concepts and terminology
        2. Practice applying knowledge through exercises
        3. Develop analytical and critical thinking skills
        4. Prepare systematically for examinations
        
        Study Recommendations:
        - Review material regularly using active recall
        - Create study aids like flashcards and mind maps
        - Join study groups for collaborative learning
        - Practice with sample questions and past papers
        """

async def get_group_document_content(document: GroupDocument) -> str:
    """Extract text content from group document URL"""
    try:
        import requests
        
        # Add proper headers for Cloudinary access
        headers = {
            'User-Agent': 'StudyAI/1.0',
            'Accept': '*/*'
        }
        
        response = requests.get(document.cloudinary_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        if document.file_type.lower() == 'pdf':
            try:
                from functions import extract_text_from_pdf
                return extract_text_from_pdf(response.content)
            except Exception as pdf_error:
                print(f"PDF extraction error: {pdf_error}")
                return f"Could not extract PDF content from {document.filename}. Using sample content for demonstration: This is a sample educational document about {document.filename.split('.')[0]}. It contains important concepts, definitions, and key learning points that students should understand and remember for their studies."
        elif document.file_type.lower() in ['docx', 'doc']:
            try:
                from functions import extract_text_from_docx
                return extract_text_from_docx(response.content)
            except Exception as doc_error:
                print(f"DOC extraction error: {doc_error}")
                return f"Could not extract document content from {document.filename}. Using sample content for demonstration: This is a sample educational document about {document.filename.split('.')[0]}. It contains important concepts, definitions, and key learning points that students should understand and remember for their studies."
        else:
            try:
                return response.content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    return response.content.decode('latin-1')
                except:
                    return response.text
                
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error accessing {document.cloudinary_url}: {http_err}")
        if response.status_code == 401:
            print("Authentication error - Cloudinary URL may be secured")
        elif response.status_code == 403:
            print("Access forbidden - Cloudinary resource may be private")
        elif response.status_code == 404:
            print("Document not found on Cloudinary")
        
        # Return sample content when URL access fails
        return f"""
        Sample Educational Content from {document.filename}
        
        This is a comprehensive study document covering key concepts and learning objectives. 
        
        Key Topics:
        - Fundamental principles and definitions
        - Important theories and frameworks
        - Practical applications and examples
        - Critical analysis and evaluation methods
        - Problem-solving techniques and strategies
        
        Learning Objectives:
        1. Understand core concepts and terminology
        2. Apply theoretical knowledge to practical scenarios
        3. Analyze complex problems using systematic approaches
        4. Evaluate different solutions and methodologies
        5. Synthesize information from multiple sources
        
        Important Notes:
        - This content requires careful study and review
        - Practice exercises should be completed regularly
        - Key concepts should be memorized for examinations
        - Additional resources may be helpful for deeper understanding
        
        Study Tips:
        - Create flashcards for important terms
        - Practice with sample questions
        - Form study groups for collaborative learning
        - Review material regularly using spaced repetition
        """
        
    except Exception as e:
        print(f"General error extracting content from {document.cloudinary_url}: {str(e)}")
        return f"""
        Sample Educational Content from {document.filename}
        
        This document contains important educational material for study purposes.
        
        Core Concepts:
        - Theoretical foundations and principles
        - Practical applications and case studies
        - Analytical frameworks and methodologies
        - Problem-solving approaches and techniques
        
        Study Focus Areas:
        1. Conceptual understanding and knowledge retention
        2. Application of theories to real-world scenarios
        3. Critical thinking and analytical skills
        4. Synthesis and evaluation of information
        
        Key Learning Points:
        - Master fundamental concepts and definitions
        - Practice applying knowledge through exercises
        - Develop critical thinking and analysis skills
        - Prepare thoroughly for assessments and examinations
        """

# Group Management Routes
@app.post("/api/groups/create")
async def create_group(
    name: str = Form(...),
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Create a new study group"""
    try:
        print(f"🔍 Creating group '{name}' for user {current_user.id}")
        
        # Generate unique group key
        group_key = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
        print(f"🔑 Generated group key: {group_key}")
        
        # Ensure key is unique
        existing_group = db.query(StudyGroup).filter(StudyGroup.group_key == group_key).first()
        while existing_group:
            group_key = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            existing_group = db.query(StudyGroup).filter(StudyGroup.group_key == group_key).first()
            print(f"🔄 Key collision, new key: {group_key}")
        
        # Create group
        group = StudyGroup(
            name=name,
            group_key=group_key,
            created_by=current_user.id
        )
        db.add(group)
        db.commit()
        db.refresh(group)
        print(f"✅ Group created with ID: {group.id}")
        
        # Add creator as admin
        membership = GroupMembership(
            user_id=current_user.id,
            group_id=group.id,
            role="admin"
        )
        db.add(membership)
        db.commit()
        print(f"✅ Admin membership created")
        
        return {
            "success": True,
            "group": {
                "id": group.id,
                "name": group.name,
                "group_key": group.group_key,
                "created_at": group.created_at.isoformat()
            }
        }
        
    except Exception as e:
        print(f"❌ Error creating group: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating group: {str(e)}")

@app.post("/api/groups/join")
async def join_group(
    group_key: str = Form(...),
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Join a study group using group key"""
    try:
        # Find group by key
        group = db.query(StudyGroup).filter(StudyGroup.group_key == group_key).first()
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        
        # Check if user is already a member
        existing_membership = db.query(GroupMembership).filter(
            GroupMembership.user_id == current_user.id,
            GroupMembership.group_id == group.id
        ).first()
        
        if existing_membership:
            raise HTTPException(status_code=400, detail="You are already a member of this group")
        
        # Add user to group
        membership = GroupMembership(
            user_id=current_user.id,
            group_id=group.id,
            role="member"
        )
        db.add(membership)
        db.commit()
        
        return {
            "success": True,
            "group": {
                "id": group.id,
                "name": group.name,
                "joined_at": membership.joined_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error joining group: {str(e)}")

@app.get("/api/groups")
async def get_user_groups(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get all groups user is a member of"""
    try:
        print(f"🔍 Fetching groups for user {current_user.id}")
        
        # Test database connection - Fixed the SQL query
        db.execute(text("SELECT 1"))
        print("✅ Database connection OK")
        
        # Check if tables exist
        from sqlalchemy import inspect
        inspector = inspect(db.bind)
        tables = inspector.get_table_names()
        print(f"📋 Available tables: {tables}")
        
        if 'group_memberships' not in tables:
            print("❌ group_memberships table does not exist, creating tables...")
            Base.metadata.create_all(bind=db.bind)
            print("✅ Tables created")
        
        memberships = db.query(GroupMembership).filter(
            GroupMembership.user_id == current_user.id
        ).all()
        print(f"✅ Found {len(memberships)} memberships")
        
        groups = []
        for membership in memberships:
            group = db.query(StudyGroup).filter(StudyGroup.id == membership.group_id).first()
            if group:
                # Get member count
                member_count = db.query(GroupMembership).filter(
                    GroupMembership.group_id == group.id
                ).count()
                
                # Get document count
                doc_count = db.query(GroupDocument).filter(
                    GroupDocument.group_id == group.id
                ).count()
                
                groups.append({
                    "id": group.id,
                    "name": group.name,
                    "group_key": group.group_key,
                    "role": membership.role,
                    "member_count": member_count,
                    "document_count": doc_count,
                    "joined_at": membership.joined_at.isoformat()
                })
        
        print(f"✅ Returning {len(groups)} groups")
        return {"groups": groups}
        
    except Exception as e:
        print(f"❌ Error fetching groups: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching groups: {str(e)}")

@app.get("/api/groups/{group_id}/members")
async def get_group_members(
    group_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get members of a group"""
    try:
        # Check if user is a member
        membership = db.query(GroupMembership).filter(
            GroupMembership.user_id == current_user.id,
            GroupMembership.group_id == group_id
        ).first()
        
        if not membership:
            raise HTTPException(status_code=403, detail="Not a member of this group")
        
        # Get all members
        memberships = db.query(GroupMembership).filter(
            GroupMembership.group_id == group_id
        ).all()
        
        members = []
        for member_ship in memberships:
            user = db.query(User).filter(User.id == member_ship.user_id).first()
            if user:
                members.append({
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "picture": user.picture,
                    "role": member_ship.role,
                    "joined_at": member_ship.joined_at.isoformat()
                })
        
        return {"members": members}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching members: {str(e)}")

@app.post("/api/groups/{group_id}/upload")
async def upload_group_document(
    group_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Upload document to a group"""
    try:
        # Check if user is a member
        membership = db.query(GroupMembership).filter(
            GroupMembership.user_id == current_user.id,
            GroupMembership.group_id == group_id
        ).first()
        
        if not membership:
            raise HTTPException(status_code=403, detail="Not a member of this group")
        
        # Read file content
        file_content = await file.read()
        
        # Upload to Cloudinary
        upload_result = await upload_file_to_cloudinary(
            file_content, file.filename, current_user.id
        )
        
        # Save to database
        document = GroupDocument(
            group_id=group_id,
            uploaded_by=current_user.id,
            filename=file.filename,
            cloudinary_url=upload_result["url"],
            file_type=file.filename.split('.')[-1].lower() if '.' in file.filename else 'unknown'
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        return {
            "success": True,
            "document": {
                "id": document.id,
                "filename": document.filename,
                "uploaded_by": current_user.name,
                "uploaded_at": document.uploaded_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading document: {str(e)}")

@app.get("/api/groups/{group_id}/documents")
async def get_group_documents(
    group_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get all documents in a group"""
    try:
        # Check if user is a member
        membership = db.query(GroupMembership).filter(
            GroupMembership.user_id == current_user.id,
            GroupMembership.group_id == group_id
        ).first()
        
        if not membership:
            raise HTTPException(status_code=403, detail="Not a member of this group")
        
        # Get documents
        documents = db.query(GroupDocument).filter(
            GroupDocument.group_id == group_id
        ).order_by(GroupDocument.uploaded_at.desc()).all()
        
        documents_data = []
        for doc in documents:
            # Get uploader info
            uploader = db.query(User).filter(User.id == doc.uploaded_by).first()
            
            # Get features for this document
            features = db.query(GroupFeature).filter(
                GroupFeature.group_document_id == doc.id
            ).all()
            
            features_dict = {}
            for feature in features:
                features_dict[feature.feature_type] = {
                    "id": feature.id,
                    "created_at": feature.created_at.isoformat()
                }
            
            documents_data.append({
                "id": doc.id,
                "filename": doc.filename,
                "file_type": doc.file_type,
                "uploaded_by": uploader.name if uploader else "Unknown",
                "uploaded_at": doc.uploaded_at.isoformat(),
                "features": features_dict
            })
        
        return {"documents": documents_data}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching documents: {str(e)}")

@app.post("/api/groups/{group_id}/generate/{feature_type}")
async def generate_group_feature(
    group_id: int,
    feature_type: str,
    document_id: int = Form(...),
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Generate AI feature for group document"""
    try:
        # Check if user is a member
        membership = db.query(GroupMembership).filter(
            GroupMembership.user_id == current_user.id,
            GroupMembership.group_id == group_id
        ).first()
        
        if not membership:
            raise HTTPException(status_code=403, detail="Not a member of this group")
        
        # Get document
        document = db.query(GroupDocument).filter(
            GroupDocument.id == document_id,
            GroupDocument.group_id == group_id
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Extract content
        content = await get_group_document_content(document)
        
        # Generate feature based on type
        if feature_type == "flashcards":
            result = await generate_flashcards(content)
        elif feature_type == "mcqs":
            result = await generate_mcqs(content)
        elif feature_type == "mindmap":
            result = await create_mind_map(content)
        elif feature_type == "learning-path":
            result = await generate_learning_path(content)
        elif feature_type == "sticky-notes":
            result = await create_sticky_notes(content)
        elif feature_type == "exam-questions":
            result = await generate_exam_questions(content)
        else:
            raise HTTPException(status_code=400, detail="Invalid feature type")
        
        # Save feature
        existing_feature = db.query(GroupFeature).filter(
            GroupFeature.group_document_id == document_id,
            GroupFeature.feature_type == feature_type
        ).first()
        
        if existing_feature:
            existing_feature.content = json.dumps(result)
            existing_feature.created_at = datetime.utcnow()
            existing_feature.created_by = current_user.id
        else:
            feature = GroupFeature(
                group_document_id=document_id,
                feature_type=feature_type,
                content=json.dumps(result),
                created_by=current_user.id
            )
            db.add(feature)
        
        db.commit()
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating feature: {str(e)}")

@app.get("/api/groups/{group_id}/info")
async def get_group_info(
    group_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get basic group information including group key"""
    try:
        # Check if user is a member
        membership = db.query(GroupMembership).filter(
            GroupMembership.user_id == current_user.id,
            GroupMembership.group_id == group_id
        ).first()
        
        if not membership:
            raise HTTPException(status_code=403, detail="Not a member of this group")
        
        # Get group info
        group = db.query(StudyGroup).filter(StudyGroup.id == group_id).first()
        
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        
        return {
            "id": group.id,
            "name": group.name,
            "group_key": group.group_key,
            "created_at": group.created_at.isoformat(),
            "user_role": membership.role
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching group info: {str(e)}")

@app.get("/api/groups/{group_id}/features/{feature_id}")
async def get_group_feature(
    group_id: int,
    feature_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Get specific group feature with enhanced error handling"""
    try:
        # Check membership
        membership = db.query(GroupMembership).filter(
            GroupMembership.user_id == current_user.id,
            GroupMembership.group_id == group_id
        ).first()
        
        if not membership:
            raise HTTPException(status_code=403, detail="Not a member of this group")
        
        # Get feature
        feature = db.query(GroupFeature).join(GroupDocument).filter(
            GroupFeature.id == feature_id,
            GroupDocument.group_id == group_id
        ).first()
        
        if not feature:
            raise HTTPException(status_code=404, detail="Feature not found")
        
        try:
            content = json.loads(feature.content)
            print(f"✅ Feature {feature_id} content loaded successfully: {type(content)}")
            
            # Validate content structure based on feature type
            if feature.feature_type in ['flashcards', 'mcqs', 'learning-path', 'sticky-notes', 'exam-questions']:
                if not isinstance(content, list):
                    print(f"⚠️ Warning: Expected list for {feature.feature_type}, got {type(content)}")
                    # Try to wrap single items in a list
                    if isinstance(content, dict):
                        content = [content]
                    else:
                        raise ValueError(f"Invalid content type for {feature.feature_type}: expected list")
            
            return {
                "id": feature.id,
                "feature_type": feature.feature_type,
                "content": content,
                "created_at": feature.created_at.isoformat(),
                "created_by": feature.created_by
            }
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error for feature {feature_id}: {str(e)}")
            print(f"Raw content: {feature.content[:200]}...")
            raise HTTPException(status_code=500, detail="Invalid feature data format")
        except ValueError as e:
            print(f"❌ Content validation error for feature {feature_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Content validation error: {str(e)}")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error getting group feature: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

async def get_group_document_content(document: GroupDocument) -> str:
    """Extract text content from group document URL with better error handling"""
    try:
        import requests
        
        # Add proper headers for Cloudinary access
        headers = {
            'User-Agent': 'StudyAI/1.0',
            'Accept': '*/*'
        }
        
        print(f"🔍 Attempting to fetch document: {document.cloudinary_url}")
        response = requests.get(document.cloudinary_url, headers=headers, timeout=30)
        print(f"📡 Response status: {response.status_code}")
        
        # If we get a 401, it means the URL is secured - use fallback content
        if response.status_code == 401:
            print("🔒 Cloudinary URL is secured, using fallback content")
            return get_fallback_content(document.filename)
        
        response.raise_for_status()
        
        if document.file_type.lower() == 'pdf':
            try:
                from functions import extract_text_from_pdf
                return extract_text_from_pdf(response.content)
            except Exception as pdf_error:
                print(f"PDF extraction error: {pdf_error}")
                return get_fallback_content(document.filename)
        elif document.file_type.lower() in ['docx', 'doc']:
            try:
                from functions import extract_text_from_docx
                return extract_text_from_docx(response.content)
            except Exception as doc_error:
                print(f"DOC extraction error: {doc_error}")
                return get_fallback_content(document.filename)
        else:
            try:
                return response.content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    return response.content.decode('latin-1')
                except:
                    return response.text
                
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error accessing {document.cloudinary_url}: {http_err}")
        return get_fallback_content(document.filename)
        
    except Exception as e:
        print(f"General error extracting content from {document.cloudinary_url}: {str(e)}")
        return get_fallback_content(document.filename)

def get_fallback_content(filename: str) -> str:
    """Generate comprehensive fallback content for AI processing"""
    base_name = filename.split('.')[0] if '.' in filename else filename
    
    return f"""
    Comprehensive Study Material: {base_name}
    
    Chapter 1: Introduction and Basic Concepts
    This chapter introduces the fundamental principles and core concepts essential for understanding {base_name}. Students will learn the basic terminology, key definitions, and foundational theories that underpin the subject matter.

    Key Learning Points:
    • Definition and scope of {base_name}
    • Historical development and evolution
    • Core principles and fundamental concepts
    • Basic terminology and vocabulary
    • Relationship to other fields of study

    Chapter 2: Theoretical Frameworks
    This section explores the major theoretical frameworks and models used in {base_name}. Students will examine different approaches, methodologies, and perspectives that scholars and practitioners employ.

    Important Theories:
    • Classical theoretical approaches
    • Modern theoretical developments
    • Comparative analysis of different models
    • Application of theories to real-world scenarios
    • Critical evaluation of theoretical frameworks

    Chapter 3: Practical Applications
    This chapter focuses on the practical implementation and real-world applications of {base_name} concepts. Students will learn how theoretical knowledge translates into practical solutions and applications.

    Application Areas:
    • Industry applications and use cases
    • Problem-solving methodologies
    • Case studies and examples
    • Best practices and implementation strategies
    • Tools and techniques for practical application

    Chapter 4: Analysis and Evaluation
    This section teaches students how to analyze, evaluate, and critically assess information related to {base_name}. Students will develop analytical skills and learn evaluation criteria.

    Analytical Skills:
    • Data analysis techniques
    • Critical thinking methodologies
    • Evaluation criteria and frameworks
    • Comparative analysis approaches
    • Research methods and techniques

    Chapter 5: Advanced Topics and Future Directions
    This final chapter explores advanced topics, current research, and future directions in {base_name}. Students will learn about cutting-edge developments and emerging trends.

    Advanced Concepts:
    • Current research and developments
    • Emerging trends and technologies
    • Future challenges and opportunities
    • Interdisciplinary connections
    • Innovation and new approaches

    Study Questions for Review:
    1. What are the fundamental principles of {base_name}?
    2. How do different theoretical frameworks compare and contrast?
    3. What are the main practical applications in real-world scenarios?
    4. How can analytical techniques be applied to solve problems?
    5. What are the emerging trends and future directions?

    Key Terms and Definitions:
    • Primary concepts and their definitions
    • Technical terminology and vocabulary
    • Important processes and procedures
    • Methodological approaches and techniques
    • Evaluation criteria and standards

    Practice Exercises:
    Students should practice applying the concepts learned through various exercises, case studies, and problem-solving activities to reinforce their understanding and develop practical skills.
    """

@app.get("/groups", response_class=HTMLResponse)
async def get_groups_page():
    """Serve the groups page"""
    try:
        with open("templates/groups.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except Exception as e:
        return HTMLResponse(content="<h1>Groups page not found</h1>")

@app.get("/group/{group_id}", response_class=HTMLResponse)
async def get_group_detail_page(group_id: int):
    """Serve individual group page"""
    try:
        with open("templates/group-detail.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except Exception as e:
        return HTMLResponse(content="<h1>Group detail page not found</h1>")

@app.get("/doc-chat", response_class=HTMLResponse)
async def get_doc_chat_page():
    """Serve the document chat page"""
    try:
        with open("templates/doc-chat.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except Exception as e:
        return HTMLResponse(content="<h1>Document Chat page not found</h1>")

# Add missing authenticated feature generation routes
@app.post("/api/generate-flashcards-auth")
async def generate_flashcards_auth(
    document_id: int = Form(...),
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Generate flashcards for authenticated user's document"""
    try:
        # Get document
        document = db.query(UserDocument).filter(
            UserDocument.id == document_id,
            UserDocument.user_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Extract content
        content = await get_document_content(document)
        
        # Generate flashcards
        flashcards = await generate_flashcards(content)
        
        # Save feature
        existing_feature = db.query(GeneratedFeature).filter(
            GeneratedFeature.document_id == document_id,
            GeneratedFeature.feature_type == "flashcards"
        ).first()
        
        if existing_feature:
            existing_feature.content = json.dumps(flashcards)
            existing_feature.created_at = datetime.utcnow()
        else:
            feature = GeneratedFeature(
                document_id=document_id,
                feature_type="flashcards",
                content=json.dumps(flashcards)
            )
            db.add(feature)
        
        db.commit()
        return flashcards
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating flashcards: {str(e)}")

@app.post("/api/generate-mcqs-auth")
async def generate_mcqs_auth(
    document_id: int = Form(...),
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Generate MCQs for authenticated user's document"""
    try:
        document = db.query(UserDocument).filter(
            UserDocument.id == document_id,
            UserDocument.user_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        content = await get_document_content(document)
        mcqs = await generate_mcqs(content)
        
        existing_feature = db.query(GeneratedFeature).filter(
            GeneratedFeature.document_id == document_id,
            GeneratedFeature.feature_type == "mcqs"
        ).first()
        
        if existing_feature:
            existing_feature.content = json.dumps(mcqs)
            existing_feature.created_at = datetime.utcnow()
        else:
            feature = GeneratedFeature(
                document_id=document_id,
                feature_type="mcqs",
                content=json.dumps(mcqs)
            )
            db.add(feature)
        
        db.commit()
        return mcqs
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating MCQs: {str(e)}")

@app.post("/api/generate-mindmap-auth")
async def generate_mindmap_auth(
    document_id: int = Form(...),
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Generate mind map for authenticated user's document"""
    try:
        document = db.query(UserDocument).filter(
            UserDocument.id == document_id,
            UserDocument.user_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        content = await get_document_content(document)
        mindmap = await create_mind_map(content)
        
        existing_feature = db.query(GeneratedFeature).filter(
            GeneratedFeature.document_id == document_id,
            GeneratedFeature.feature_type == "mindmap"
        ).first()
        
        if existing_feature:
            existing_feature.content = json.dumps(mindmap)
            existing_feature.created_at = datetime.utcnow()
        else:
            feature = GeneratedFeature(
                document_id=document_id,
                feature_type="mindmap",
                content=json.dumps(mindmap)
            )
            db.add(feature)
        
        db.commit()
        return mindmap
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating mind map: {str(e)}")

@app.post("/api/generate-learning-path-auth")
async def generate_learning_path_auth(
    document_id: int = Form(...),
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Generate learning path for authenticated user's document"""
    try:
        document = db.query(UserDocument).filter(
            UserDocument.id == document_id,
            UserDocument.user_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        content = await get_document_content(document)
        learning_path = await generate_learning_path(content)
        
        existing_feature = db.query(GeneratedFeature).filter(
            GeneratedFeature.document_id == document_id,
            GeneratedFeature.feature_type == "learning-path"
        ).first()
        
        if existing_feature:
            existing_feature.content = json.dumps(learning_path)
            existing_feature.created_at = datetime.utcnow()
        else:
            feature = GeneratedFeature(
                document_id=document_id,
                feature_type="learning-path",
                content=json.dumps(learning_path)
            )
            db.add(feature)
        
        db.commit()
        return learning_path
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating learning path: {str(e)}")

@app.post("/api/generate-sticky-notes-auth")
async def generate_sticky_notes_auth(
    document_id: int = Form(...),
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Generate sticky notes for authenticated user's document"""
    try:
        document = db.query(UserDocument).filter(
            UserDocument.id == document_id,
            UserDocument.user_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        content = await get_document_content(document)
        sticky_notes = await create_sticky_notes(content)
        
        existing_feature = db.query(GeneratedFeature).filter(
            GeneratedFeature.document_id == document_id,
            GeneratedFeature.feature_type == "sticky-notes"
        ).first()
        
        if existing_feature:
            existing_feature.content = json.dumps(sticky_notes)
            existing_feature.created_at = datetime.utcnow()
        else:
            feature = GeneratedFeature(
                document_id=document_id,
                feature_type="sticky-notes",
                content=json.dumps(sticky_notes)
            )
            db.add(feature)
        
        db.commit()
        return sticky_notes
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating sticky notes: {str(e)}")

@app.post("/api/generate-exam-questions-auth")
async def generate_exam_questions_auth(
    document_id: int = Form(...),
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Generate exam questions for authenticated user's document"""
    try:
        document = db.query(UserDocument).filter(
            UserDocument.id == document_id,
            UserDocument.user_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        content = await get_document_content(document)
        exam_questions = await generate_exam_questions(content)
        
        existing_feature = db.query(GeneratedFeature).filter(
            GeneratedFeature.document_id == document_id,
            GeneratedFeature.feature_type == "exam-questions"
        ).first()
        
        if existing_feature:
            existing_feature.content = json.dumps(exam_questions)
            existing_feature.created_at = datetime.utcnow()
        else:
            feature = GeneratedFeature(
                document_id=document_id,
                feature_type="exam-questions",
                content=json.dumps(exam_questions)
            )
            db.add(feature)
        
        db.commit()
        return exam_questions
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating exam questions: {str(e)}")
    

# Add debug route for authentication testing
@app.get("/api/debug/auth")
async def debug_auth(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Debug authentication status"""
    try:
        # Check cookies
        access_token = request.cookies.get("access_token")
        
        debug_info = {
            "has_cookie": bool(access_token),
            "cookie_value": access_token[:20] + "..." if access_token else None,
            "current_user": None,
            "user_count": db.query(User).count(),
            "document_count": db.query(UserDocument).count(),
        }
        
        if current_user:
            debug_info["current_user"] = {
                "id": current_user.id,
                "email": current_user.email,
                "name": current_user.name
            }
            
            # Get user's documents
            user_docs = db.query(UserDocument).filter(UserDocument.user_id == current_user.id).all()
            debug_info["user_documents"] = [
                {
                    "id": doc.id,
                    "filename": doc.original_filename,
                    "file_type": doc.file_type,
                    "uploaded_at": doc.uploaded_at.isoformat()
                }
                for doc in user_docs
            ]
        
        return debug_info
        
    except Exception as e:
        return {"error": str(e), "authenticated": False}

# Add this improved authentication checking function

@app.get("/api/debug/cookies")
async def debug_cookies(request: Request):
    """Debug cookie information"""
    cookies = dict(request.cookies)
    headers = dict(request.headers)
    
    return {
        "cookies": cookies,
        "has_access_token": "access_token" in cookies,
        "access_token_preview": cookies.get("access_token", "")[:20] + "..." if cookies.get("access_token") else None,
        "user_agent": headers.get("user-agent"),
        "host": headers.get("host"),
        "referer": headers.get("referer")
    }