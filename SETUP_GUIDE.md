# DANCER Full Stack Setup Guide

This guide will help you set up and run the complete DANCER application with both frontend and backend.

## System Overview

- **Frontend**: Vue.js application (port 5173)
- **Backend**: FastAPI Python server (port 8000)
- **Storage**: AWS S3 bucket for video files
- **Database**: SQLite for metadata (configurable to PostgreSQL)

## Prerequisites

- Node.js (v16 or higher)
- Python 3.8+
- AWS account with S3 access
- Git

## Quick Start

### 1. Frontend Setup

```bash
# Install frontend dependencies
npm install

# Start the Vue.js development server
npm run dev
```

The frontend will be available at: `http://localhost:5173`

### 2. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Configure environment variables
cp config.env.example .env

# Edit .env with your AWS credentials:
# AWS_ACCESS_KEY_ID=your_access_key
# AWS_SECRET_ACCESS_KEY=your_secret_key
# S3_BUCKET=your-bucket-name

# Start the backend server
python start.py
```

The backend API will be available at: `http://localhost:8000`

### 3. AWS S3 Setup

1. Create an S3 bucket in your AWS account
2. Create an IAM user with the following permissions:
   - `s3:PutObject`
   - `s3:GetObject`
   - `s3:ListBucket`
3. Generate access keys for the IAM user
4. Add the credentials to your `.env` file

## Usage

1. **Open the application**: Navigate to `http://localhost:5173`
2. **Submit a file**: Click "Submit file" and select a video
3. **Fill metadata**: Complete all required fields:
   - User ID
   - Subject ID
   - Activity
   - Shoe type
   - Acquisition date/time
4. **Upload**: Click "Finalize submission" to upload to S3

## Features

### Frontend Features
- ✅ Responsive design with 1440×1024px layout
- ✅ File selection with validation
- ✅ Metadata form with validation
- ✅ Real-time upload progress
- ✅ Success/error messaging
- ✅ Professional UI with rounded corners and consistent styling

### Backend Features
- ✅ Secure S3 upload with server-side AWS credentials
- ✅ File type validation (videos only)
- ✅ Metadata storage in database
- ✅ Complete audit trail
- ✅ RESTful API with documentation
- ✅ Error handling and logging

## API Endpoints

- `GET /` - Health check
- `GET /health` - Detailed health status
- `POST /upload` - Upload video and metadata
- `GET /uploads/{upload_id}` - Get upload information
- `GET /docs` - Interactive API documentation

## File Structure

```
dancer-app/
├── src/                    # Vue.js frontend
│   ├── App.vue            # Main application component
│   ├── assets/            # Static assets and styles
│   └── ...
├── backend/               # Python FastAPI backend
│   ├── main.py           # Main application
│   ├── requirements.txt  # Python dependencies
│   ├── start.py          # Startup script
│   └── README.md         # Backend documentation
├── package.json          # Frontend dependencies
└── SETUP_GUIDE.md        # This file
```

## Troubleshooting

### Common Issues

1. **CORS errors**: Make sure backend is running on port 8000
2. **AWS errors**: Check credentials and bucket permissions
3. **Upload failures**: Ensure file is a video format
4. **Database errors**: Check file permissions for SQLite

### Development Tips

- Use browser dev tools to monitor network requests
- Check backend logs for detailed error information
- Test API endpoints using `/docs` interface
- Use `.env` file for local development secrets

## Production Deployment

For production deployment:

1. **Frontend**: Build and deploy to CDN/static hosting
2. **Backend**: Deploy to cloud service (AWS ECS, Google Cloud Run, etc.)
3. **Database**: Use managed PostgreSQL service
4. **Security**: Use proper CORS settings and HTTPS
5. **Monitoring**: Set up logging and monitoring

## Next Steps

- Add user authentication
- Implement video processing pipeline
- Add download functionality
- Set up automated testing
- Add file preview capabilities
