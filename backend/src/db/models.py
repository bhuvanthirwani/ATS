from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON, Text
from sqlalchemy.orm import relationship
from .session import Base
from datetime import datetime
import uuid

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    
    workflows = relationship("Workflow", back_populates="user")

class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Metadata
    job_description = Column(Text, nullable=True)
    profile_filename = Column(String, nullable=True)
    template_filename = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="workflows")
    jobs = relationship("Job", back_populates="workflow", cascade="all, delete-orphan")

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True) # Celery Task ID
    workflow_id = Column(String, ForeignKey("workflows.id"))
    
    status = Column(String, default="PENDING") # PENDING, SUCCESS, FAILED
    result_data = Column(JSON, nullable=True) # Store the OptimizationResult/RefineResult
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    workflow = relationship("Workflow", back_populates="jobs")
