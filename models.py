from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text

from .database import Base

class RawFile(Base):
    __tablename__ = "raw_files"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    path = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

class ProcessedFile(Base):
    __tablename__ = "processed_files"
    id = Column(Integer, primary_key=True, index=True)
    raw_file_id = Column(Integer, ForeignKey("raw_files.id"), nullable=False)
    output_path = Column(String, nullable=False)
    processed_at = Column(DateTime, default=datetime.utcnow)

class JobLog(Base):
    __tablename__ = "job_logs"
    id = Column(Integer, primary_key=True, index=True)
    raw_file_id = Column(Integer, ForeignKey("raw_files.id"), nullable=False)
    status = Column(String, nullable=False)  # e.g., 'pending', 'success', 'error'
    message = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
