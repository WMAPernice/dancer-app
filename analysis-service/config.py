"""
Configuration management for DANCER Analysis Service
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
env_file_path = os.path.join(os.path.dirname(__file__), '.env')
env_file_loaded = False
if os.path.exists(env_file_path):
    load_dotenv(env_file_path)
    env_file_loaded = True
else:
    env_file_loaded = False

class Config:
    """Configuration class for analysis service"""
    
    # AWS Configuration
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    
    # S3 Configuration
    S3_BUCKET = os.getenv("S3_BUCKET", "dancer-uploads")
    S3_PREFIX = os.getenv("S3_PREFIX", "uploads")
    
    # SQS Configuration
    SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")
    SQS_QUEUE_NAME = os.getenv("SQS_QUEUE_NAME", "dancer-upload-notifications")
    SQS_WAIT_TIME = int(os.getenv("SQS_WAIT_TIME", "20"))  # Long polling wait time
    SQS_VISIBILITY_TIMEOUT = int(os.getenv("SQS_VISIBILITY_TIMEOUT", "300"))  # 5 minutes
    SQS_MAX_MESSAGES = int(os.getenv("SQS_MAX_MESSAGES", "10"))  # Max messages per poll
    
    # S3 Event Notification Validation
    EXPECTED_S3_EVENT_SOURCE = os.getenv("EXPECTED_S3_EVENT_SOURCE", "aws:s3")
    EXPECTED_S3_EVENT_PREFIX = os.getenv("EXPECTED_S3_EVENT_PREFIX", "ObjectCreated")
    
    # Processing Configuration
    DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "./temp_downloads")
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", "2"))
    CLEANUP_AFTER_PROCESSING = os.getenv("CLEANUP_AFTER_PROCESSING", "true").lower() == "true"
    POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "5"))  # Sleep between polling cycles
    MAX_RUNTIME_HOURS = float(os.getenv("MAX_RUNTIME_HOURS", "1.0"))  # Maximum runtime in hours (0 = unlimited)
    
    # Database Configuration (reuse from main backend)
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dancer_uploads.db")
    
    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        missing = []
        
        if not cls.AWS_ACCESS_KEY_ID:
            missing.append("AWS_ACCESS_KEY_ID")
        if not cls.AWS_SECRET_ACCESS_KEY:
            missing.append("AWS_SECRET_ACCESS_KEY")
        if not cls.SQS_QUEUE_URL and not cls.SQS_QUEUE_NAME:
            missing.append("SQS_QUEUE_URL or SQS_QUEUE_NAME")
            
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        # Create download directory if it doesn't exist
        os.makedirs(cls.DOWNLOAD_DIR, exist_ok=True)
        
        return True
    
    @classmethod
    def print_env_status(cls):
        """Print environment file loading status"""
        import sys
        if env_file_loaded:
            print(f"✅ Environment file loaded: {env_file_path}")
        else:
            print(f"⚠️  No .env file found at: {env_file_path}")
            print("   Environment variables will be loaded from system environment only")
        
        # Force output to appear immediately
        sys.stdout.flush()
    
    @classmethod
    def print_config(cls):
        """Print configuration summary (without secrets)"""
        print("\n🔧 Analysis Service Configuration:")
        print(f"   AWS Region: {cls.AWS_REGION}")
        print(f"   S3 Bucket: {cls.S3_BUCKET}")
        print(f"   S3 Prefix: {cls.S3_PREFIX}")
        print(f"   SQS Queue: {cls.SQS_QUEUE_NAME}")
        print(f"   Download Dir: {cls.DOWNLOAD_DIR}")
        print(f"   Max Workers: {cls.MAX_WORKERS}")
        print(f"   Cleanup Files: {cls.CLEANUP_AFTER_PROCESSING}")
        print(f"   Poll Interval: {cls.POLL_INTERVAL_SECONDS}s")
        print(f"   Max Runtime: {cls.MAX_RUNTIME_HOURS}h")
        print(f"   Has AWS Credentials: {bool(cls.AWS_ACCESS_KEY_ID and cls.AWS_SECRET_ACCESS_KEY)}")
        
        # Force output to appear immediately
        import sys
        sys.stdout.flush()
