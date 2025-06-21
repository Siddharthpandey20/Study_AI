import google.generativeai as genai
import PyPDF2
import docx
import json
import re
import uuid
from typing import List, Dict, Any
from io import BytesIO
import asyncio
from fastapi import UploadFile
import pandas as pd
from datetime import datetime, timedelta
import os

# Configure Gemini API with error handling - NO DEFAULT VALUES
try:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is required")
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    AI_AVAILABLE = True
except Exception as e:
    print(f"Warning: AI model not available: {e}")
    AI_AVAILABLE = False
    model = None

# Utility Functions
async def process_uploaded_file(file: UploadFile) -> str:
    """Process uploaded file and extract text content"""
    try:
        content = await file.read()
        file_extension = file.filename.split('.')[-1].lower()
        
        if file_extension == 'pdf':
            return extract_text_from_pdf(content)
        elif file_extension == 'docx':
            return extract_text_from_docx(content)
        elif file_extension == 'txt':
            return content.decode('utf-8')
        elif file_extension == 'md':
            return content.decode('utf-8')
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
    except Exception as e:
        raise Exception(f"Error processing file: {str(e)}")

def extract_text_from_pdf(content: bytes) -> str:
    """Extract text from PDF content"""
    try:
        pdf_reader = PyPDF2.PdfReader(BytesIO(content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        raise Exception(f"Error extracting PDF text: {str(e)}")

def extract_text_from_docx(content: bytes) -> str:
    """Extract text from DOCX content"""
    try:
        doc = docx.Document(BytesIO(content))
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        raise Exception(f"Error extracting DOCX text: {str(e)}")

def preprocess_content_for_ai(content: str) -> str:
    """Preprocess content to optimize for AI processing"""
    try:
        # Remove excessive whitespace
        content = ' '.join(content.split())
        
        # Remove common artifacts from video transcripts
        video_artifacts = [
            '[Music]', '[Applause]', '[Laughter]', '(inaudible)', 
            '(music playing)', '[sound effects]', '>>>', '<<<'
        ]
        
        for artifact in video_artifacts:
            content = content.replace(artifact, '')
        
        # Clean up punctuation issues common in transcripts
        content = content.replace(' ,', ',').replace(' .', '.')
        content = content.replace('  ', ' ').strip()
        
        return content
        
    except Exception as e:
        print(f"Error preprocessing content: {e}")
        return content

# 🔥 1. Smart Revision Mode Functions
async def generate_flashcards(content: str) -> List[Dict[str, Any]]:
    """Generate flashcards using Gemini AI with enhanced preprocessing"""
    try:
        if not AI_AVAILABLE or not model:
            return create_fallback_flashcards(content)
        
        # Preprocess content for better AI understanding
        processed_content = preprocess_content_for_ai(content)
        
        # Truncate if too long (leave room for prompt)
        if len(processed_content) > 3500:
            processed_content = processed_content[:3500]
            # Try to end at a complete sentence
            last_period = processed_content.rfind('.')
            if last_period > 3000:
                processed_content = processed_content[:last_period + 1]
            
        prompt = f"""
Based on the following educational content, generate 8 high-quality flashcards for effective studying.

REQUIREMENTS:
- Create clear, specific questions with concise answers
- Focus on key concepts, definitions, and important facts
- Vary difficulty levels: easy (2-3 cards), medium (3-4 cards), hard (2-3 cards)
- Make questions test understanding, not just memorization
- Ensure answers are complete but brief

CONTENT: {processed_content}

Return ONLY a valid JSON array with this exact structure:
[
    {{
        "id": "fc_1",
        "question": "Clear, specific question about key concept",
        "answer": "Concise, accurate answer",
        "difficulty": "easy"
    }}
]
        """
        
        response = model.generate_content(prompt)
        flashcards_text = response.text.strip()
        
        # Clean the response text
        flashcards_text = flashcards_text.replace('```json', '').replace('```', '').strip()
        
        # Extract JSON from response
        try:
            flashcards_json = json.loads(flashcards_text)
            
            # Ensure we have a list
            if not isinstance(flashcards_json, list):
                return create_fallback_flashcards(content)
            
            # Validate and clean up structure
            for i, flashcard in enumerate(flashcards_json):
                if not isinstance(flashcard, dict):
                    continue
                if 'id' not in flashcard:
                    flashcard['id'] = f"fc_{i+1}"
                if 'question' not in flashcard or len(flashcard['question'].strip()) < 5:
                    flashcard['question'] = f"What is important about: {processed_content[:50]}...?"
                if 'answer' not in flashcard or len(flashcard['answer'].strip()) < 5:
                    flashcard['answer'] = "Review the key concepts from the material"
                if 'difficulty' not in flashcard or flashcard['difficulty'] not in ['easy', 'medium', 'hard']:
                    flashcard['difficulty'] = ["easy", "medium", "hard"][i % 3]
            
            return flashcards_json[:8]  # Limit to 8 flashcards
            
        except json.JSONDecodeError:
            return create_fallback_flashcards(content)
            
    except Exception as e:
        print(f"Error in generate_flashcards: {e}")
        return create_fallback_flashcards(content)

async def generate_mcqs(content: str) -> List[Dict[str, Any]]:
    """Generate MCQs using Gemini AI with enhanced preprocessing"""
    try:
        if not AI_AVAILABLE or not model:
            return create_fallback_mcqs(content)
        
        # Preprocess content
        processed_content = preprocess_content_for_ai(content)
        
        # Truncate if needed
        if len(processed_content) > 3500:
            processed_content = processed_content[:3500]
            last_period = processed_content.rfind('.')
            if last_period > 3000:
                processed_content = processed_content[:last_period + 1]
            
        prompt = f"""
Based on the following educational content, generate 6 multiple choice questions for comprehensive testing.

REQUIREMENTS:
- Create questions that test understanding and application
- Each question must have exactly 4 options (A, B, C, D)
- Only 1 correct answer per question
- Make incorrect options plausible but clearly wrong
- Provide clear explanations for correct answers
- Mix difficulty levels appropriately

CONTENT: {processed_content}

Return ONLY a valid JSON array with this exact structure:
[
    {{
        "id": "mcq_1",
        "question": "Clear, specific question about the content?",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "correct_answer": 0,
        "explanation": "Brief explanation of why this is correct",
        "difficulty": "medium"
    }}
]
        """
        
        response = model.generate_content(prompt)
        mcqs_text = response.text.strip()
        
        # Clean the response
        mcqs_text = mcqs_text.replace('```json', '').replace('```', '').strip()
        
        try:
            mcqs_json = json.loads(mcqs_text)
            
            if not isinstance(mcqs_json, list):
                return create_fallback_mcqs(content)
            
            # Validate and fix structure
            for i, mcq in enumerate(mcqs_json):
                if not isinstance(mcq, dict):
                    continue
                if 'id' not in mcq:
                    mcq['id'] = f"mcq_{i+1}"
                if 'question' not in mcq or len(mcq['question'].strip()) < 5:
                    mcq['question'] = f"What is the main concept in: {processed_content[:60]}...?"
                if 'options' not in mcq or not isinstance(mcq['options'], list) or len(mcq['options']) != 4:
                    mcq['options'] = [
                        "Primary concept from content",
                        "Secondary information", 
                        "Unrelated information",
                        "Incorrect interpretation"
                    ]
                if 'correct_answer' not in mcq or not isinstance(mcq['correct_answer'], int) or mcq['correct_answer'] not in [0, 1, 2, 3]:
                    mcq['correct_answer'] = 0
                if 'explanation' not in mcq or len(mcq['explanation'].strip()) < 10:
                    mcq['explanation'] = "This option correctly represents the main concept discussed in the content."
                if 'difficulty' not in mcq or mcq['difficulty'] not in ['easy', 'medium', 'hard']:
                    mcq['difficulty'] = ["easy", "medium", "hard"][i % 3]
            
            return mcqs_json[:6]
            
        except json.JSONDecodeError:
            return create_fallback_mcqs(content)
            
    except Exception as e:
        print(f"Error in generate_mcqs: {e}")
        return create_fallback_mcqs(content)

# 🧠 2. Mind Map Generator Functions
async def create_mind_map(content: str) -> Dict[str, Any]:
    """Generate mind map structure using Gemini AI with enhanced preprocessing"""
    try:
        if not AI_AVAILABLE or not model:
            return create_fallback_mindmap(content)
        
        processed_content = preprocess_content_for_ai(content)
        
        if len(processed_content) > 3500:
            processed_content = processed_content[:3500]
            last_period = processed_content.rfind('.')
            if last_period > 3000:
                processed_content = processed_content[:last_period + 1]
            
        prompt = f"""
Analyze the following educational content and create a hierarchical mind map structure.

REQUIREMENTS:
- Create 1 central topic and 3-4 main branches
- Each main branch should have 2-3 subtopics
- Use clear, concise labels (max 25 characters each)
- Organize information logically
- Use appropriate colors for visual appeal

CONTENT: {processed_content}

Return ONLY a valid JSON object with this exact structure:
{{
    "title": "Main Topic (max 30 chars)",
    "nodes": [
        {{
            "id": "node_1",
            "label": "Topic 1",
            "level": 1,
            "color": "#FF6B6B",
            "children": [
                {{
                    "id": "node_1_1",
                    "label": "Subtopic 1.1",
                    "level": 2,
                    "color": "#4ECDC4",
                    "children": []
                }}
            ]
        }}
    ]
}}
        """
        
        response = model.generate_content(prompt)
        mindmap_text = response.text.strip()
        
        # Clean response
        mindmap_text = mindmap_text.replace('```json', '').replace('```', '').strip()
        
        try:
            mindmap_json = json.loads(mindmap_text)
            
            # Validate structure
            if 'title' not in mindmap_json or len(mindmap_json['title']) == 0:
                mindmap_json['title'] = "Content Overview"
            if 'nodes' not in mindmap_json or not isinstance(mindmap_json['nodes'], list):
                mindmap_json['nodes'] = []
            
            # Ensure title is not too long
            if len(mindmap_json['title']) > 40:
                mindmap_json['title'] = mindmap_json['title'][:37] + "..."
                
            return mindmap_json
            
        except json.JSONDecodeError:
            return create_fallback_mindmap(content)
            
    except Exception as e:
        print(f"Error in create_mind_map: {e}")
        return create_fallback_mindmap(content)

# 🎯 3. Learning Path Generator Functions
async def generate_learning_path(content: str) -> List[Dict[str, Any]]:
    """Generate step-by-step learning path using Gemini AI with fallback"""
    try:
        if not AI_AVAILABLE or not model:
            return create_fallback_learning_path(content)
            
        prompt = f"""
        Based on the following content, create a 5-step learning path.
        Break down the learning process into logical, sequential steps.

        Content: {content[:3000]}

        Return ONLY a valid JSON array with this exact structure:
        [
            {{
                "step_number": 1,
                "title": "Step Title",
                "description": "What to learn in this step",
                "estimated_time": "30 minutes",
                "prerequisites": [],
                "resources": ["Content material"]
            }}
        ]
        """
        
        response = model.generate_content(prompt)
        path_text = response.text.strip()
        
        # Clean response
        path_text = path_text.replace('```json', '').replace('```', '').strip()
        
        try:
            path_json = json.loads(path_text)
            
            if not isinstance(path_json, list):
                return create_fallback_learning_path(content)
                
            # Validate structure
            for i, step in enumerate(path_json):
                if 'step_number' not in step:
                    step['step_number'] = i + 1
                if 'title' not in step:
                    step['title'] = f"Learning Step {i + 1}"
                if 'description' not in step:
                    step['description'] = "Continue learning from the content"
                if 'estimated_time' not in step:
                    step['estimated_time'] = "30 minutes"
                if 'prerequisites' not in step:
                    step['prerequisites'] = []
                if 'resources' not in step:
                    step['resources'] = ["Study material"]
            
            return path_json[:5]
            
        except json.JSONDecodeError:
            return create_fallback_learning_path(content)
            
    except Exception as e:
        print(f"Error in generate_learning_path: {e}")
        return create_fallback_learning_path(content)

# 🎨 4. Context-Aware Sticky Notes Functions
async def create_sticky_notes(content: str) -> List[Dict[str, Any]]:
    """Generate smart color-coded sticky notes with fallback"""
    try:
        if not AI_AVAILABLE or not model:
            return create_fallback_sticky_notes(content)
            
        prompt = f"""
        Analyze the following content and create 8 smart sticky notes with color coding:
        - RED (category: "red"): Must memorize - critical facts, formulas, definitions
        - YELLOW (category: "yellow"): Good to know - important concepts
        - GREEN (category: "green"): Bonus/Extra - interesting additional info

        Content: {content[:3000]}

        Return ONLY a valid JSON array with this exact structure:
        [
            {{
                "id": "note_1",
                "content": "Key point or fact",
                "category": "red",
                "priority": 8,
                "tags": ["important", "definition"]
            }}
        ]
        """
        
        response = model.generate_content(prompt)
        notes_text = response.text.strip()
        
        # Clean response
        notes_text = notes_text.replace('```json', '').replace('```', '').strip()
        
        try:
            notes_json = json.loads(notes_text)
            
            if not isinstance(notes_json, list):
                return create_fallback_sticky_notes(content)
            
            # Validate structure
            for i, note in enumerate(notes_json):
                if 'id' not in note:
                    note['id'] = f"note_{i+1}"
                if 'content' not in note:
                    note['content'] = "Important point"
                if 'category' not in note or note['category'] not in ['red', 'yellow', 'green']:
                    note['category'] = ['red', 'yellow', 'green'][i % 3]
                if 'priority' not in note:
                    note['priority'] = 5
                if 'tags' not in note:
                    note['tags'] = ["study"]
            
            return notes_json[:8]
            
        except json.JSONDecodeError:
            return create_fallback_sticky_notes(content)
            
    except Exception as e:
        print(f"Error in create_sticky_notes: {e}")
        return create_fallback_sticky_notes(content)

# 🔹 5. Exam Booster Mode Functions
async def generate_exam_questions(content: str) -> List[Dict[str, Any]]:
    """Generate exam questions with probability scores and fallback"""
    try:
        if not AI_AVAILABLE or not model:
            return create_fallback_exam_questions(content)
            
        prompt = f"""
        Based on the following content, predict 6 most likely exam questions.
        Categorize them as: "short_answer", "long_answer", or "hots"
        Assign probability scores between 0.5 and 1.0.

        Content: {content[:3000]}

        Return ONLY a valid JSON array with this exact structure:
        [
            {{
                "id": "eq_1",
                "question": "Predicted exam question",
                "type": "short_answer",
                "probability_score": 0.85,
                "difficulty": "medium",
                "keywords": ["key", "words"]
            }}
        ]
        """
        
        response = model.generate_content(prompt)
        questions_text = response.text.strip()
        
        # Clean response
        questions_text = questions_text.replace('```json', '').replace('```', '').strip()
        
        try:
            questions_json = json.loads(questions_text)
            
            if not isinstance(questions_json, list):
                return create_fallback_exam_questions(content)
            
            # Validate structure
            for i, question in enumerate(questions_json):
                if 'id' not in question:
                    question['id'] = f"eq_{i+1}"
                if 'question' not in question:
                    question['question'] = f"Exam question {i+1}"
                if 'type' not in question or question['type'] not in ['short_answer', 'long_answer', 'hots']:
                    question['type'] = ['short_answer', 'long_answer', 'hots'][i % 3]
                if 'probability_score' not in question:
                    question['probability_score'] = 0.7
                if 'difficulty' not in question:
                    question['difficulty'] = "medium"
                if 'keywords' not in question:
                    question['keywords'] = ["important"]
            
            return questions_json[:6]
            
        except json.JSONDecodeError:
            return create_fallback_exam_questions(content)
            
    except Exception as e:
        print(f"Error in generate_exam_questions: {e}")
        return create_fallback_exam_questions(content)

def classify_question_importance(question: str, content: str) -> float:
    """Classify question importance using simple keyword matching"""
    important_keywords = ['definition', 'formula', 'principle', 'law', 'theorem', 'concept']
    question_lower = question.lower()
    
    score = 0.5  # Base score
    for keyword in important_keywords:
        if keyword in question_lower:
            score += 0.1
    
    return min(score, 1.0)

# Enhanced Fallback Functions
def create_fallback_flashcards(content: str) -> List[Dict[str, Any]]:
    """Create enhanced flashcards when AI generation fails"""
    sentences = [s.strip() for s in content.split('.') if len(s.strip()) > 20][:8]
    flashcards = []
    
    for i, sentence in enumerate(sentences):
        flashcards.append({
            "id": f"fc_{i+1}",
            "question": f"What is mentioned about: {sentence[:60]}...?",
            "answer": sentence,
            "difficulty": ["easy", "medium", "hard"][i % 3]
        })
    
    # Ensure we have at least 3 flashcards
    while len(flashcards) < 3:
        flashcards.append({
            "id": f"fc_{len(flashcards)+1}",
            "question": "What are the key points in this content?",
            "answer": "Review the main concepts from the uploaded material.",
            "difficulty": "medium"
        })
    
    return flashcards

def create_fallback_mcqs(content: str) -> List[Dict[str, Any]]:
    """Create enhanced MCQs when AI generation fails"""
    words = content.split()[:100]
    key_topics = [word for word in words if len(word) > 5][:5]
    
    mcqs = []
    for i, topic in enumerate(key_topics):
        mcqs.append({
            "id": f"mcq_{i+1}",
            "question": f"What is the significance of '{topic}' in this content?",
            "options": [
                f"It is a key concept",
                f"It is mentioned briefly",
                f"It is not important",
                f"It is irrelevant"
            ],
            "correct_answer": 0,
            "explanation": f"'{topic}' appears to be significant based on the content analysis.",
            "difficulty": "medium"
        })
    
    # Ensure we have at least 3 MCQs
    while len(mcqs) < 3:
        mcqs.append({
            "id": f"mcq_{len(mcqs)+1}",
            "question": "What is the main focus of this content?",
            "options": ["Educational material", "Entertainment", "News", "Advertisement"],
            "correct_answer": 0,
            "explanation": "This appears to be educational content based on the structure.",
            "difficulty": "easy"
        })
    
    return mcqs

def create_fallback_mindmap(content: str) -> Dict[str, Any]:
    """Create enhanced mindmap when AI generation fails"""
    sentences = [s.strip() for s in content.split('.') if len(s.strip()) > 10][:6]
    
    nodes = []
    colors = ["#FF6B6B", "#4ECDC4", "#FFE66D", "#95E1D3"]
    
    for i, sentence in enumerate(sentences[:4]):
        nodes.append({
            "id": f"node_{i+1}",
            "label": sentence[:30] + "..." if len(sentence) > 30 else sentence,
            "level": 1,
            "color": colors[i % len(colors)],
            "children": []
        })
    
    return {
        "title": "Content Overview",
        "nodes": nodes
    }

def create_fallback_learning_path(content: str) -> List[Dict[str, Any]]:
    """Create enhanced learning path when AI generation fails"""
    return [
        {
            "step_number": 1,
            "title": "Initial Reading",
            "description": "Read through the entire content to get an overview",
            "estimated_time": "20 minutes",
            "prerequisites": [],
            "resources": ["Original content"]
        },
        {
            "step_number": 2,
            "title": "Identify Key Concepts",
            "description": "Highlight and note down the main concepts and terms",
            "estimated_time": "15 minutes", 
            "prerequisites": ["Step 1"],
            "resources": ["Highlighter", "Notes"]
        },
        {
            "step_number": 3,
            "title": "Create Summary",
            "description": "Write a brief summary of the main points",
            "estimated_time": "25 minutes",
            "prerequisites": ["Step 1", "Step 2"],
            "resources": ["Notes", "Summary template"]
        },
        {
            "step_number": 4,
            "title": "Practice Questions",
            "description": "Test your understanding with practice questions",
            "estimated_time": "30 minutes",
            "prerequisites": ["Step 3"],
            "resources": ["Practice questions", "Answer key"]
        },
        {
            "step_number": 5,
            "title": "Review and Revise",
            "description": "Final review of all concepts and weak areas",
            "estimated_time": "20 minutes",
            "prerequisites": ["Step 4"],
            "resources": ["Summary", "Notes", "Flashcards"]
        }
    ]

def create_fallback_sticky_notes(content: str) -> List[Dict[str, Any]]:
    """Create enhanced sticky notes when AI generation fails"""
    sentences = [s.strip() for s in content.split('.') if len(s.strip()) > 15][:8]
    notes = []
    categories = ["red", "yellow", "green"]
    
    for i, sentence in enumerate(sentences):
        category = categories[i % 3]
        priority = 8 if category == "red" else 6 if category == "yellow" else 4
        
        notes.append({
            "id": f"note_{i+1}",
            "content": sentence[:100] + "..." if len(sentence) > 100 else sentence,
            "category": category,
            "priority": priority,
            "tags": ["study", "important" if category == "red" else "review"]
        })
    
    # Ensure we have at least 6 notes
    while len(notes) < 6:
        category = categories[len(notes) % 3]
        notes.append({
            "id": f"note_{len(notes)+1}",
            "content": "Review the key concepts from this section",
            "category": category,
            "priority": 5,
            "tags": ["review"]
        })
    
    return notes

def create_fallback_exam_questions(content: str) -> List[Dict[str, Any]]:
    """Create enhanced exam questions when AI generation fails"""
    return [
        {
            "id": "eq_1",
            "question": "Explain the main concepts discussed in this content.",
            "type": "long_answer",
            "probability_score": 0.8,
            "difficulty": "medium",
            "keywords": ["main", "concepts", "explain"]
        },
        {
            "id": "eq_2",
            "question": "List the key points mentioned in the material.",
            "type": "short_answer",
            "probability_score": 0.75,
            "difficulty": "easy",
            "keywords": ["list", "key", "points"]
        },
        {
            "id": "eq_3",
            "question": "Analyze and evaluate the significance of the topics covered.",
            "type": "hots",
            "probability_score": 0.7,
            "difficulty": "hard",
            "keywords": ["analyze", "evaluate", "significance"]
        },
        {
            "id": "eq_4",
            "question": "Define the important terms mentioned in the content.",
            "type": "short_answer",
            "probability_score": 0.85,
            "difficulty": "easy",
            "keywords": ["define", "terms", "important"]
        },
        {
            "id": "eq_5",
            "question": "Compare and contrast different concepts from the material.",
            "type": "long_answer",
            "probability_score": 0.65,
            "difficulty": "medium",
            "keywords": ["compare", "contrast", "concepts"]
        },
        {
            "id": "eq_6",
            "question": "Apply the learned concepts to solve real-world problems.",
            "type": "hots",
            "probability_score": 0.6,
            "difficulty": "hard",
            "keywords": ["apply", "real-world", "problems"]
        }
    ]

# Additional Utility Functions
def calculate_study_time(content_length: int) -> str:
    """Calculate estimated study time based on content length"""
    words = content_length // 5  # Rough word count
    minutes = max(15, words // 200 * 15)  # 15 minutes per 200 words minimum
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    if hours > 0:
        return f"{hours}h {remaining_minutes}m"
    else:
        return f"{remaining_minutes}m"

def extract_keywords(content: str, max_keywords: int = 10) -> List[str]:
    """Extract important keywords from content"""
    # Simple keyword extraction (can be enhanced with NLP libraries)
    words = re.findall(r'\b[A-Za-z]{4,}\b', content.lower())
    word_freq = {}
    
    for word in words:
        word_freq[word] = word_freq.get(word, 0) + 1
    
    # Sort by frequency and return top keywords
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word[0] for word in sorted_words[:max_keywords]]

def generate_study_schedule(learning_path: List[Dict], available_hours_per_day: int = 2) -> Dict[str, Any]:
    """Generate a study schedule based on learning path"""
    schedule = {}
    current_date = datetime.now()
    
    for step in learning_path:
        estimated_time = step.get('estimated_time', '1 hour')
        # Parse time (simple parsing)
        if 'hour' in estimated_time:
            hours = int(re.findall(r'\d+', estimated_time)[0])
        else:
            hours = 1
        
        days_needed = max(1, hours // available_hours_per_day)
        
        schedule[step['title']] = {
            'start_date': current_date.strftime('%Y-%m-%d'),
            'end_date': (current_date + timedelta(days=days_needed)).strftime('%Y-%m-%d'),
            'daily_hours': min(hours, available_hours_per_day)
        }
        
        current_date += timedelta(days=days_needed + 1)  # Add buffer day
    
    return schedule