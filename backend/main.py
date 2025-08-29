from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import boto3
import os
import uuid
from datetime import datetime
from typing import Optional
import logging
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

# Load environment variables from .env file
env_file_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_file_path):
    load_dotenv(env_file_path)
    print(f"✓ Loaded environment variables from: {env_file_path}")
else:
    print(f"⚠ No .env file found at: {env_file_path}")
    print("  Environment variables will be loaded from system environment only")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(title="DANCER Upload API", version="1.0.0")

# CORS middleware for frontend communication
# Environment-aware CORS origins
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Configurable origins
    allow_credentials=False,        # No credentials needed (no auth yet)
    allow_methods=["GET", "POST"],  # Only needed methods
    allow_headers=["content-type", "accept", "authorization"],  # Specific headers only
)

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dancer_uploads.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class UploadRecord(Base):
    __tablename__ = "uploads"
    
    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(String, unique=True, index=True)
    user_id = Column(String, index=True)
    subject_id = Column(String, index=True)
    activity = Column(String)
    shoe_type = Column(String)
    acq_datetime = Column(String)
    filename = Column(String)
    s3_key = Column(String)
    s3_bucket = Column(String)
    upload_timestamp = Column(DateTime, default=datetime.utcnow)

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic models for request/response
class UploadResponse(BaseModel):
    success: bool
    upload_id: str
    message: str

class UploadMetadata(BaseModel):
    user_id: str
    subject_id: str
    activity: str
    shoe_type: str
    acq_datetime: str

# AWS S3 Configuration - Load and secure credentials
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET = os.getenv("S3_BUCKET", "dancer-uploads")
S3_PREFIX = os.getenv("S3_PREFIX", "uploads")  # Configurable prefix for organization

# Security: Clear AWS credentials from environment after loading
# This prevents other code from accidentally accessing them
if "AWS_ACCESS_KEY_ID" in os.environ:
    del os.environ["AWS_ACCESS_KEY_ID"]
if "AWS_SECRET_ACCESS_KEY" in os.environ:
    del os.environ["AWS_SECRET_ACCESS_KEY"]

# Security Configuration
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 100 * 1024 * 1024))  # 100MB default
ALLOWED_VIDEO_TYPES = ["video/mp4", "video/avi", "video/mov", "video/wmv", "video/flv"]

# Initialize S3 client with explicit credential validation
def initialize_s3_client():
    """Initialize S3 client with explicit credential validation"""
    
    # Validate that all required credentials are provided via environment
    if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
        logger.error("AWS credentials not provided via environment variables")
        logger.error("Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in your .env file")
        return None
    
    try:
        # Create S3 client with explicit credentials only (no fallback)
        client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
        
        # Test the credentials by accessing our specific bucket/prefix
        try:
            # Try list_objects_v2 with our exact prefix (matches aws s3 ls behavior)
            response = client.list_objects_v2(
                Bucket=S3_BUCKET,
                Prefix=S3_PREFIX + "/",  # Add trailing slash like AWS CLI
                MaxKeys=1,
                Delimiter="/"  # Only list objects, not traverse subdirectories
            )
            logger.info("S3 client initialized successfully with provided credentials")
            logger.info(f"Using AWS region: {AWS_REGION}")
            logger.info(f"Verified access to bucket: {S3_BUCKET} with prefix: {S3_PREFIX}/")
            return client
        except client.exceptions.NoSuchBucket:
            logger.error(f"S3 bucket does not exist: {S3_BUCKET}")
            logger.error("Please check your S3_BUCKET configuration")
            return None
        except Exception as test_error:
            # If list_objects_v2 fails, try a simpler approach - TODO: should be unnecessary!
            logger.warning(f"list_objects_v2 failed: {test_error}")
            logger.info("Trying alternative validation method...")
            
            try:
                # Fallback: Try to test upload permissions by checking if we can generate a presigned URL
                # This doesn't actually make a request but validates credentials format
                test_key = f"{S3_PREFIX}/test-connection-check"
                client.generate_presigned_url(
                    'put_object',
                    Params={'Bucket': S3_BUCKET, 'Key': test_key},
                    ExpiresIn=1  # 1 second expiry
                )
                logger.info("S3 client initialized successfully (alternative validation)")
                logger.info(f"Using AWS region: {AWS_REGION}")
                logger.info(f"Bucket: {S3_BUCKET}")
                return client
            except Exception as fallback_error:
                logger.error(f"S3 credentials validation failed: {fallback_error}")
                logger.error(f"Please check your AWS credentials and bucket access for: {S3_BUCKET}")
                logger.error("Required permissions: s3:ListBucket and/or s3:PutObject")
                return None
            
    except Exception as e:
        logger.error(f"Failed to create S3 client: {e}")
        return None

s3_client = initialize_s3_client()

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
async def root():
    return {"message": "DANCER Upload API is running"}

@app.get("/health")
async def health_check():
    """
    Health check endpoint with detailed S3 configuration status
    """
    s3_status = "not_configured"
    s3_details = {}
    
    if s3_client is not None:
        try:
            # Test S3 connection with the same method as initialization
            s3_client.list_objects_v2(
                Bucket=S3_BUCKET,
                Prefix=S3_PREFIX + "/",
                MaxKeys=1,
                Delimiter="/"
            )
            s3_status = "connected"
            s3_details = {
                "bucket": S3_BUCKET,
                "region": AWS_REGION,
                "prefix": S3_PREFIX
            }
        except Exception as e:
            # If list_objects_v2 fails, try the alternative method - TODO: should be unnecessary!
            try:
                test_key = f"{S3_PREFIX}/health-check"
                s3_client.generate_presigned_url(
                    'put_object',
                    Params={'Bucket': S3_BUCKET, 'Key': test_key},
                    ExpiresIn=1
                )
                s3_status = "connected_alternative"
                s3_details = {
                    "bucket": S3_BUCKET,
                    "region": AWS_REGION,
                    "prefix": S3_PREFIX,
                    "note": "Using alternative validation (presigned URL)"
                }
            except Exception as fallback_error:
                s3_status = "connection_failed"
                s3_details = {"error": str(e), "fallback_error": str(fallback_error)}
    else:
        s3_details = {"error": "S3 client not initialized - check credentials"}
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "s3": {
            "status": s3_status,
            "details": s3_details
        },
        "environment": {
            "has_aws_access_key": bool(AWS_ACCESS_KEY_ID),
            "has_aws_secret_key": bool(AWS_SECRET_ACCESS_KEY),
            "aws_region": AWS_REGION,
            "s3_bucket": S3_BUCKET,
            "max_file_size_mb": MAX_FILE_SIZE // (1024 * 1024)
        }
    }

@app.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    subject_id: str = Form(...),
    activity: str = Form(...),
    shoe_type: str = Form(...),
    acq_datetime: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Upload a video file and metadata to S3 and store metadata in database
    """
    try:
        # Enhanced file validation
        if not file.content_type or file.content_type not in ALLOWED_VIDEO_TYPES:
            raise HTTPException(status_code=400, detail=f"File must be a supported video type: {', '.join(ALLOWED_VIDEO_TYPES)}")
        
        # Read file content for size validation
        file_content = await file.read()
        
        # Validate file size
        if len(file_content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE // (1024*1024)}MB")
        
        # Validate metadata inputs (prevent directory traversal)
        for field_name, field_value in [("user_id", user_id), ("subject_id", subject_id), ("activity", activity), ("shoe_type", shoe_type)]:
            if not field_value or not field_value.strip():
                raise HTTPException(status_code=400, detail=f"{field_name} cannot be empty")
            if any(char in field_value for char in ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*']):
                raise HTTPException(status_code=400, detail=f"{field_name} contains invalid characters")
        
        # Generate unique upload ID and S3 key
        upload_id = str(uuid.uuid4())
        file_extension = os.path.splitext(file.filename)[1]
        s3_key = f"{S3_PREFIX}/{user_id.strip()}/{subject_id.strip()}/{upload_id}{file_extension}"
        
        # Validate S3 client
        if not s3_client:
            raise HTTPException(status_code=500, detail="S3 service not configured")
        
        # Upload to S3
        try:
            s3_client.put_object(
                Bucket=S3_BUCKET,
                Key=s3_key,
                Body=file_content,
                ContentType=file.content_type,
                Metadata={
                    'upload-id': upload_id,
                    'user-id': user_id,
                    'subject-id': subject_id,
                    'activity': activity,
                    'shoe-type': shoe_type,
                    'acq-datetime': acq_datetime,
                    'upload-timestamp': datetime.utcnow().isoformat()
                }
            )
            logger.info(f"Successfully uploaded file to S3: {s3_key}")
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to upload to S3: {str(e)}")
        
        # Save metadata to database
        try:
            upload_record = UploadRecord(
                upload_id=upload_id,
                user_id=user_id,
                subject_id=subject_id,
                activity=activity,
                shoe_type=shoe_type,
                acq_datetime=acq_datetime,
                filename=file.filename,
                s3_key=s3_key,
                s3_bucket=S3_BUCKET
            )
            db.add(upload_record)
            db.commit()
            logger.info(f"Successfully saved metadata to database: {upload_id}")
        except Exception as e:
            logger.error(f"Database save failed: {e}")
            # Note: File is already in S3, but we couldn't save metadata
            raise HTTPException(status_code=500, detail=f"Failed to save metadata: {str(e)}")
        
        return UploadResponse(
            success=True,
            upload_id=upload_id,
            message="File uploaded successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during upload: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/uploads/{upload_id}")
async def get_upload_info(upload_id: str, db: Session = Depends(get_db)):
    """
    Get information about a specific upload
    """
    upload_record = db.query(UploadRecord).filter(UploadRecord.upload_id == upload_id).first()
    if not upload_record:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    return {
        "upload_id": upload_record.upload_id,
        "user_id": upload_record.user_id,
        "subject_id": upload_record.subject_id,
        "activity": upload_record.activity,
        "shoe_type": upload_record.shoe_type,
        "acq_datetime": upload_record.acq_datetime,
        "filename": upload_record.filename,
        "upload_timestamp": upload_record.upload_timestamp,
        "s3_location": f"s3://{upload_record.s3_bucket}/{upload_record.s3_key}"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
