# .env File Configuration Guide

## The Problem You Identified

You're absolutely correct! Just creating a `.env` file **does not automatically work** without proper loading code.

### What Doesn't Work:
```bash
# 1. Create .env file
echo "AWS_ACCESS_KEY_ID=your_key" > backend/.env

# 2. Run main.py directly
python backend/main.py

# 3. Result: FAILS!
# ERROR: AWS credentials not provided via environment variables
```

### Why It Fails:
- `os.getenv()` only reads **system environment variables**
- `.env` files are just text files - they don't automatically become environment variables
- Python needs explicit code to load `.env` files

## How .env Loading Works in DANCER

### Method 1: Using start.py (Recommended)
```bash
cd backend
python start.py  # ✅ This works!
```

**Why it works:**
```python
# start.py loads .env file first
load_dotenv(env_file)
print(f"✓ Loaded environment variables from {env_file}")

# Then imports main.py (which uses the loaded variables)
from main import app
```

### Method 2: Using main.py directly (Now Fixed)
```bash
cd backend
python main.py  # ✅ Now this works too!
```

**Why it now works:**
```python
# main.py now loads .env at the top
from dotenv import load_dotenv
load_dotenv()  # Loads .env file before reading environment variables
```

## Complete Setup Workflow

### 1. Create .env File
```bash
cd backend
cp config.env.example .env
```

### 2. Edit .env File
```bash
# Edit .env with your actual credentials
AWS_ACCESS_KEY_ID=AKIA1234567890ABCDEF
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=us-east-1
S3_BUCKET=your-bucket-name
S3_PREFIX=uploads
MAX_FILE_SIZE=104857600
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

### 3. Run the Server
```bash
# Method A: Using start script (recommended)
python start.py

# Method B: Direct execution
python main.py

# Method C: Using uvicorn
uvicorn main:app --reload
```

## What Happens During Startup

### With .env File Present:
```bash
✓ Loaded environment variables from: /path/to/backend/.env
INFO:S3 client initialized successfully with provided credentials
INFO:Using AWS region: us-east-1
🚀 Starting DANCER API server...
```

### Without .env File:
```bash
⚠ No .env file found at: /path/to/backend/.env
  Environment variables will be loaded from system environment only
ERROR:AWS credentials not provided via environment variables
ERROR:Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in your .env file
```

## Alternative Ways to Provide Environment Variables

### Option 1: .env File (Recommended for Development)
```bash
# Create .env file
echo "AWS_ACCESS_KEY_ID=your_key" > .env
python start.py
```

### Option 2: System Environment Variables
```bash
# Export variables in shell
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
python start.py
```

### Option 3: Inline Environment Variables
```bash
# Set variables for single command
AWS_ACCESS_KEY_ID=your_key AWS_SECRET_ACCESS_KEY=your_secret python start.py
```

### Option 4: Shell Script
```bash
# Create run.sh
#!/bin/bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
python start.py
```

## Environment Variable Priority

The `python-dotenv` library follows this precedence order:

1. **System environment variables** (highest priority)
2. **.env file variables** (if system vars don't exist)
3. **Default values in code** (lowest priority)

### Example:
```bash
# .env file contains:
AWS_REGION=us-west-2

# System environment has:
export AWS_REGION=us-east-1

# Result: us-east-1 (system env wins)
```

## Security Best Practices

### ✅ Good Practices:
```bash
# 1. Never commit .env to git
echo ".env" >> .gitignore

# 2. Use config.env.example as template
cp config.env.example .env

# 3. Set restrictive file permissions
chmod 600 .env

# 4. Use different .env files per environment
# .env.development
# .env.staging  
# .env.production
```

### ❌ Bad Practices:
```bash
# DON'T commit real credentials
git add .env  # ❌ Never do this!

# DON'T hardcode credentials in code
AWS_ACCESS_KEY_ID = "AKIA1234567890ABCDEF"  # ❌ Security risk!

# DON'T use production credentials in development
```

## Troubleshooting

### Problem: "No .env file found"
```bash
# Check file location
ls -la backend/.env

# Ensure you're in the right directory
cd backend
python start.py
```

### Problem: "AWS credentials not provided"
```bash
# Check .env file contents
cat backend/.env

# Verify no extra spaces or quotes
AWS_ACCESS_KEY_ID=your_key   # ✅ Good
AWS_ACCESS_KEY_ID = your_key # ❌ Spaces around =
AWS_ACCESS_KEY_ID="your_key" # ❌ Unnecessary quotes
```

### Problem: Variables not loading
```bash
# Test loading manually
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('AWS_ACCESS_KEY_ID'))"
```

## Production Deployment

### Docker Environment
```dockerfile
# Copy .env file
COPY .env .env

# Or use build args
ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY
ENV AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID
ENV AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY
```

### Cloud Deployment
```bash
# Use cloud provider's secret management
# AWS: Systems Manager Parameter Store
# Google Cloud: Secret Manager
# Azure: Key Vault

# Inject secrets as environment variables
# Don't use .env files in production!
```

This guide explains why your observation was correct - just creating a `.env` file wouldn't work without the proper loading mechanism that we've now implemented!
