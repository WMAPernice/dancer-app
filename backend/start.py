#!/usr/bin/env python3
"""
Startup script for DANCER backend API
"""

import os
import sys
from dotenv import load_dotenv

def main():
    # Load environment variables from .env file if it exists
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_file):
        load_dotenv(env_file)
        print(f"✓ Loaded environment variables from {env_file}")
    else:
        print(f"⚠ No .env file found at {env_file}")
        print("  Make sure to set AWS credentials as environment variables or create a .env file")
    
    # Check required environment variables
    required_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'S3_BUCKET']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("   Please set these variables or create a .env file based on config.env.example")
        return False
    
    print("✓ All required environment variables are set")
    
    # Import and run the FastAPI app
    try:
        import uvicorn
        from main import app
        
        print("🚀 Starting DANCER API server...")
        print("   API docs will be available at: http://localhost:8000/docs")
        print("   Health check at: http://localhost:8000/health")
        
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=8000,
            log_level="info"
        )
        
    except ImportError as e:
        print(f"❌ Failed to import dependencies: {e}")
        print("   Please install requirements: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
