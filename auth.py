from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db, User
from itsdangerous import URLSafeTimedSerializer
import os
import jwt
import requests
from datetime import datetime, timedelta


# Google OAuth configuration - NO DEFAULT VALUES
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
SECRET_KEY = os.getenv("SECRET_KEY")

# Validate required environment variables
if not GOOGLE_CLIENT_ID:
    raise ValueError("GOOGLE_CLIENT_ID environment variable is required")
if not GOOGLE_CLIENT_SECRET:
    raise ValueError("GOOGLE_CLIENT_SECRET environment variable is required")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required")

oauth = OAuth()

# Initialize OAuth with proper token handling configuration
oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    authorize_url='https://accounts.google.com/o/oauth2/v2/auth',
    access_token_url='https://oauth2.googleapis.com/token',
    jwks_uri='https://www.googleapis.com/oauth2/v3/certs',  # Add JWKS URI
    client_kwargs={
        'scope': 'openid email profile',
        'prompt': 'select_account'
    }
)

security = HTTPBearer(auto_error=False)
serializer = URLSafeTimedSerializer(SECRET_KEY)

def create_access_token(user_id: int, email: str):
    """Create JWT access token"""
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(days=30)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_token(token: str):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def get_current_user(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """Get current authenticated user"""
    token = None
    
    # Try to get token from Authorization header
    if credentials:
        token = credentials.credentials
    
    # Try to get token from cookie
    if not token:
        token = request.cookies.get("access_token")
    
    if not token:
        return None
    
    payload = verify_token(token)
    if not payload:
        return None
    
    user = db.query(User).filter(User.id == payload["user_id"]).first()
    return user

def require_auth(current_user: User = Depends(get_current_user)):
    """Require authentication"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return current_user

def exchange_code_for_token(code: str, redirect_uri: str):
    """Manually exchange authorization code for access token"""
    try:
        token_url = 'https://oauth2.googleapis.com/token'
        
        data = {
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri
        }
        
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        
        return response.json()
    except Exception as e:
        print(f"Error exchanging code for token: {e}")
        raise Exception(f"Token exchange failed: {str(e)}")

def get_user_info_from_token(access_token: str):
    """Get user info from Google using access token"""
    try:
        userinfo_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(userinfo_url, headers=headers)
        response.raise_for_status()
        
        return response.json()
    except Exception as e:
        print(f"Error getting user info: {e}")
        raise Exception(f"Failed to get user info: {str(e)}")

# Print OAuth configuration for debugging (only in development)
if os.getenv("DEBUG", "false").lower() == "true":
    print("✅ OAuth configured successfully")
    print(f"   Client ID: {GOOGLE_CLIENT_ID[:20]}...")
    print(f"   Authorize URL: https://accounts.google.com/o/oauth2/v2/auth")
    print(f"   Token URL: https://oauth2.googleapis.com/token")
else:
    print("✅ OAuth configured for production")
