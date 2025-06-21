import os
import re
import tempfile
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled

# Set up Gemini API - NO DEFAULT VALUES
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is required")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# Lazy load heavy dependencies
_whisper_model = None
_yt_dlp = None


def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        import whisper

        _whisper_model = whisper.load_model("medium")  # Use base model for faster processing
    return _whisper_model


def get_yt_dlp():
    global _yt_dlp
    if _yt_dlp is None:
        import yt_dlp

        _yt_dlp = yt_dlp
    return _yt_dlp


def get_video_id(youtube_url: str) -> str:
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", youtube_url)
    return match.group(1) if match else None


def get_transcript(video_id: str):
    """Fetch YouTube transcript if available."""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return transcript
    except TranscriptsDisabled:
        return None
    except Exception:
        return None


def download_audio(video_url: str) -> str:
    """Download YouTube audio as MP3."""
    yt_dlp = get_yt_dlp()

    # Create a temporary file that persists
    temp_dir = tempfile.mkdtemp()
    audio_path = os.path.join(temp_dir, "audio.%(ext)s")

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': audio_path,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        # Find the actual downloaded file
        mp3_path = audio_path.replace('%(ext)s', 'mp3')
        if os.path.exists(mp3_path):
            return mp3_path
        else:
            # Fallback: find any audio file in the temp directory
            for file in os.listdir(temp_dir):
                if file.endswith(('.mp3', '.m4a', '.wav')):
                    return os.path.join(temp_dir, file)
            raise Exception("No audio file found after download")

    except Exception as e:
        raise Exception(f"Failed to download audio: {str(e)}")


def transcribe_audio(audio_path: str) -> str:
    """Transcribe MP3 audio using Whisper."""
    try:
        whisper_model = get_whisper_model()
        result = whisper_model.transcribe(audio_path)

        # Clean up the temporary file
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
                # Also remove the temp directory if empty
                temp_dir = os.path.dirname(audio_path)
                if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                    os.rmdir(temp_dir)
        except:
            pass  # Ignore cleanup errors

        return result["text"]
    except Exception as e:
        raise Exception(f"Failed to transcribe audio: {str(e)}")


def optimize_text_for_processing(text: str, max_length: int = 3000) -> str:
    """Optimize text for AI processing by reducing tokens and cleaning content"""
    try:
        # Remove excessive whitespace and newlines
        text = ' '.join(text.split())
        
        # Remove common filler words and phrases
        filler_words = [
            'um', 'uh', 'like', 'you know', 'basically', 'actually', 'literally',
            'so basically', 'what I mean is', 'kind of', 'sort of'
        ]
        
        for filler in filler_words:
            text = text.replace(filler, '')
        
        # Remove repetitive phrases (simple approach)
        sentences = text.split('.')
        unique_sentences = []
        seen = set()
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10:  # Ignore very short sentences
                # Create a simplified version for comparison
                simplified = ' '.join(sorted(sentence.lower().split()[:5]))
                if simplified not in seen:
                    unique_sentences.append(sentence)
                    seen.add(simplified)
        
        # Rejoin sentences
        text = '. '.join(unique_sentences)
        
        # Truncate if still too long
        if len(text) > max_length:
            text = text[:max_length]
            # Try to end at a complete sentence
            last_period = text.rfind('.')
            if last_period > max_length * 0.8:  # If we can find a period in the last 20%
                text = text[:last_period + 1]
        
        # Final cleanup
        text = text.strip()
        
        return text
        
    except Exception as e:
        print(f"Error optimizing text: {e}")
        # Fallback: simple truncation
        return ' '.join(text.split())[:max_length]
def generate_summary(text: str) -> str:
    """Summarize the transcript using Gemini with optimized input"""
    try:
        # Optimize the input text first
        optimized_text = optimize_text_for_processing(text, max_length=4000)
        
        prompt = f"""
You are an expert academic summarizer. Create a comprehensive yet concise summary of this educational content.

INSTRUCTIONS:
- Focus on key concepts, main ideas, and important details
- Use clear, structured language suitable for students
- Include specific examples and explanations mentioned
- Organize information logically
- Remove redundancy and filler content
- Make it study-friendly and actionable

CONTENT: {optimized_text}

SUMMARY:
"""
        
        response = model.generate_content(prompt)
        summary = response.text.strip()
        
        # Post-process the summary
        summary = optimize_text_for_processing(summary, max_length=2000)
        
        return summary
        
    except Exception as e:
        print(f"Error generating summary: {e}")
        # Fallback summary
        return create_fallback_summary(text)

def create_fallback_summary(text: str) -> str:
    """Create a fallback summary when AI generation fails"""
    try:
        # Simple extractive summarization
        sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 20]
        
        # Take first few sentences and some from middle/end
        summary_sentences = []
        if len(sentences) > 0:
            summary_sentences.append(sentences[0])  # Opening
        if len(sentences) > 3:
            mid_point = len(sentences) // 2
            summary_sentences.extend(sentences[mid_point:mid_point+2])  # Middle
        if len(sentences) > 1:
            summary_sentences.append(sentences[-1])  # Closing
        
        summary = '. '.join(summary_sentences) + '.'
        return optimize_text_for_processing(summary, max_length=1500)
        
    except Exception as e:
        return "Summary of educational content covering key concepts and important information for study purposes."

def summarize_transcript(transcript: list) -> str:
    """Summarize transcript with optimization"""
    try:
        # Extract and clean text from transcript
        full_text = " ".join([item['text'] for item in transcript])
        
        # Pre-optimize the transcript text
        optimized_text = optimize_text_for_processing(full_text, max_length=5000)
        
        return generate_summary(optimized_text)
        
    except Exception as e:
        print(f"Error in summarize_transcript: {e}")
        return create_fallback_summary(" ".join([item.get('text', '') for item in transcript]))
