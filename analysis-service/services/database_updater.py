"""
Database Updater Service - Updates processing status and results
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy import create_engine, Column, String, DateTime, Integer, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import json

logger = logging.getLogger(__name__)

Base = declarative_base()

class ProcessingRecord(Base):
    """Database model for tracking processing status"""
    __tablename__ = "processing_records"
    
    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(String, index=True)  # Link to original upload
    s3_bucket = Column(String)
    s3_key = Column(String)
    processing_status = Column(String, default="pending")  # pending, processing, completed, failed
    processing_started = Column(DateTime, default=datetime.utcnow)
    processing_completed = Column(DateTime)
    metadata_json = Column(Text)  # JSON string of extracted metadata
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)

class DatabaseUpdater:
    """Handles database updates for processing status and results"""
    
    def __init__(self, config):
        self.config = config
        self.engine = None
        self.SessionLocal = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database connection"""
        try:
            # Use same database as main backend
            self.engine = create_engine(
                self.config.DATABASE_URL,
                connect_args={"check_same_thread": False} if "sqlite" in self.config.DATABASE_URL else {}
            )
            
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            
            # Create tables if they don't exist
            Base.metadata.create_all(bind=self.engine)
            
            logger.info("✓ Database connection initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize database: {e}")
            raise
    
    def get_db_session(self):
        """Get database session"""
        db = self.SessionLocal()
        try:
            return db
        except Exception as e:
            db.close()
            raise e
    
    async def create_processing_record(self, s3_bucket: str, s3_key: str, upload_id: Optional[str] = None) -> Optional[int]:
        """
        Create a new processing record
        
        Args:
            s3_bucket: S3 bucket name
            s3_key: S3 object key
            upload_id: Original upload ID (if available)
            
        Returns:
            Processing record ID or None if failed
        """
        try:
            db = self.get_db_session()
            
            # Extract upload_id from S3 key if not provided
            if not upload_id:
                upload_id = self._extract_upload_id_from_key(s3_key)
            
            record = ProcessingRecord(
                upload_id=upload_id,
                s3_bucket=s3_bucket,
                s3_key=s3_key,
                processing_status="processing",
                processing_started=datetime.utcnow()
            )
            
            db.add(record)
            db.commit()
            
            record_id = record.id
            db.close()
            
            logger.info(f"✓ Created processing record {record_id} for {s3_bucket}/{s3_key}")
            return record_id
            
        except Exception as e:
            logger.error(f"Failed to create processing record: {e}")
            if 'db' in locals():
                db.close()
            return None
    
    async def update_processing_status(self, record_id: int, status: str, metadata: Optional[Dict[str, Any]] = None, error_message: Optional[str] = None):
        """
        Update processing status and results
        
        Args:
            record_id: Processing record ID
            status: New status (processing, completed, failed)
            metadata: Extracted metadata (if completed)
            error_message: Error message (if failed)
        """
        try:
            db = self.get_db_session()
            
            record = db.query(ProcessingRecord).filter(ProcessingRecord.id == record_id).first()
            
            if not record:
                logger.error(f"Processing record {record_id} not found")
                db.close()
                return
            
            # Update status
            record.processing_status = status
            
            if status == "completed":
                record.processing_completed = datetime.utcnow()
                if metadata:
                    record.metadata_json = json.dumps(metadata, default=str)  # default=str handles datetime objects
            
            elif status == "failed":
                record.processing_completed = datetime.utcnow()
                if error_message:
                    record.error_message = error_message
                record.retry_count += 1
            
            db.commit()
            db.close()
            
            logger.info(f"✓ Updated processing record {record_id} to status: {status}")
            
        except Exception as e:
            logger.error(f"Failed to update processing status: {e}")
            if 'db' in locals():
                db.close()
    
    def _extract_upload_id_from_key(self, s3_key: str) -> Optional[str]:
        """
        Extract upload ID from S3 key pattern
        Expected pattern: uploads/{user_id}/{subject_id}/{upload_id}.ext
        """
        try:
            # Split the key and extract the filename
            key_parts = s3_key.split('/')
            if len(key_parts) >= 4 and key_parts[0] == "uploads":
                filename = key_parts[-1]  # Last part is the filename
                # Remove extension to get upload_id
                upload_id = filename.split('.')[0]
                return upload_id
            return None
        except Exception:
            return None
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        try:
            db = self.get_db_session()
            
            # Count records by status
            total_records = db.query(ProcessingRecord).count()
            pending_records = db.query(ProcessingRecord).filter(ProcessingRecord.processing_status == "pending").count()
            processing_records = db.query(ProcessingRecord).filter(ProcessingRecord.processing_status == "processing").count()
            completed_records = db.query(ProcessingRecord).filter(ProcessingRecord.processing_status == "completed").count()
            failed_records = db.query(ProcessingRecord).filter(ProcessingRecord.processing_status == "failed").count()
            
            # Get recent records
            recent_records = db.query(ProcessingRecord).order_by(ProcessingRecord.processing_started.desc()).limit(5).all()
            
            db.close()
            
            stats = {
                'total_records': total_records,
                'status_counts': {
                    'pending': pending_records,
                    'processing': processing_records,
                    'completed': completed_records,
                    'failed': failed_records
                },
                'recent_records': [
                    {
                        'id': r.id,
                        'upload_id': r.upload_id,
                        's3_key': r.s3_key,
                        'status': r.processing_status,
                        'started': r.processing_started.isoformat() if r.processing_started else None,
                        'completed': r.processing_completed.isoformat() if r.processing_completed else None
                    }
                    for r in recent_records
                ]
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get processing stats: {e}")
            return {'error': str(e)}
    
    async def get_failed_records(self, max_retries: int = 3) -> list:
        """Get failed records that can be retried"""
        try:
            db = self.get_db_session()
            
            failed_records = db.query(ProcessingRecord).filter(
                ProcessingRecord.processing_status == "failed",
                ProcessingRecord.retry_count < max_retries
            ).all()
            
            results = [
                {
                    'id': r.id,
                    'upload_id': r.upload_id,
                    's3_bucket': r.s3_bucket,
                    's3_key': r.s3_key,
                    'retry_count': r.retry_count,
                    'error_message': r.error_message
                }
                for r in failed_records
            ]
            
            db.close()
            return results
            
        except Exception as e:
            logger.error(f"Failed to get failed records: {e}")
            return []
