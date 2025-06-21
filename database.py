from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime
import os

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./study_ai.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# User model
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    google_id = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    picture = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    documents = relationship("UserDocument", back_populates="user")

# Document model
class UserDocument(Base):
    __tablename__ = "user_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    filename = Column(String)
    original_filename = Column(String)
    cloudinary_url = Column(String)
    file_type = Column(String)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="documents")
    features = relationship("GeneratedFeature", back_populates="document")

# Generated features model
class GeneratedFeature(Base):
    __tablename__ = "generated_features"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("user_documents.id"))
    feature_type = Column(String)  # flashcards, mcqs, mindmap, etc.
    content = Column(Text)  # JSON string of generated content
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    document = relationship("UserDocument", back_populates="features")

# Study Group models
class StudyGroup(Base):
    __tablename__ = "study_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    group_key = Column(String, unique=True, index=True, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    members = relationship("GroupMembership", back_populates="group", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by])

class GroupMembership(Base):
    __tablename__ = "group_memberships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("study_groups.id"), nullable=False)
    role = Column(String, default="member", nullable=False)  # "member" or "admin"
    joined_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    group = relationship("StudyGroup", back_populates="members")
    user = relationship("User", foreign_keys=[user_id])

class GroupDocument(Base):
    __tablename__ = "group_documents"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("study_groups.id"), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    cloudinary_url = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    group = relationship("StudyGroup", foreign_keys=[group_id])
    uploader = relationship("User", foreign_keys=[uploaded_by])
    features = relationship("GroupFeature", back_populates="document", cascade="all, delete-orphan")

class GroupFeature(Base):
    __tablename__ = "group_features"
    
    id = Column(Integer, primary_key=True, index=True)
    group_document_id = Column(Integer, ForeignKey("group_documents.id"), nullable=False)
    feature_type = Column(String, nullable=False)  # flashcards, mcqs, mindmap, etc.
    content = Column(Text, nullable=False)  # JSON string of generated content
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    document = relationship("GroupDocument", back_populates="features")
    creator = relationship("User", foreign_keys=[created_by])

# Create all tables
try:
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")
except Exception as e:
    print(f"❌ Error creating database tables: {e}")

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
