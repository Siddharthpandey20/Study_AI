#!/usr/bin/env python3
import os
import sys
import subprocess
import time

def create_directories():
    """Create necessary directories"""
    directories = ['static', 'templates', 'uploads']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Created directory: {directory}")

def check_dependencies():
    """Check if all dependencies are installed"""
    try:
        import fastapi
        import uvicorn
        import google.generativeai
        import PyPDF2
        import docx
        import pandas
        print("✓ All dependencies are installed")
        return True
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        print("Installing requirements...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        return True

def create_basic_template():
    """Create basic HTML template if it doesn't exist"""
    template_path = "templates/index.html"
    if not os.path.exists(template_path):
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart Study Tool - Loading...</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            text-align: center; 
            margin-top: 50px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
        }
        .loading {
            font-size: 1.5rem;
            margin: 2rem 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧠 Smart Study Tool</h1>
        <div class="loading">API is running successfully!</div>
        <p>Visit <a href="/docs" style="color: #a5f3fc;">/docs</a> to see the API documentation</p>
        <p>The frontend will be available once the full template is loaded.</p>
        
        <div style="margin-top: 3rem;">
            <h3>Available Features:</h3>
            <ul style="text-align: left; max-width: 500px; margin: 0 auto;">
                <li>🔥 Smart Flashcards Generation</li>
                <li>📝 MCQ Quiz Creation</li>
                <li>🧠 Interactive Mind Maps</li>
                <li>🎯 Learning Path Generator</li>
                <li>🎨 Smart Sticky Notes (Color-coded)</li>
                <li>🏆 Exam Question Predictor</li>
            </ul>
        </div>
    </div>
</body>
</html>""")
        print("✓ Created basic HTML template")

def main():
    """Main startup function"""
    print("🚀 Starting Smart Study Tool...")
    print("=" * 50)
    
    # Create directories
    create_directories()
    
    # Check dependencies
    check_dependencies()
    
    # Create basic template
    create_basic_template()
    
    print("=" * 50)
    print("✓ Setup complete!")
    print("🌟 Starting the application...")
    print("📱 Access the app at: http://localhost:8000")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("=" * 50)
    
    # Start the application
    try:
        import uvicorn
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        print("💡 Try running: python main.py")

if __name__ == "__main__":
    main()