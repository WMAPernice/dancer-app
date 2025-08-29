# DANCER Backend API

FastAPI backend for handling video uploads and metadata storage for the DANCER project.

## Features

- **File Upload**: Accepts video files with metadata
- **AWS S3 Integration**: Secure upload to S3 bucket
- **Database Storage**: SQLite/PostgreSQL for metadata tracking
- **Validation**: Server-side validation of files and metadata
- **CORS Support**: Configured for frontend integration
- **Logging**: Comprehensive logging for debugging

## Setup Instructions

### 1. Install Dependencies

#### Option A: Using pip (recommended for most users)
```bash
cd backend
pip install -r requirements.txt
```

#### Option B: Using conda (recommended for conda users)
```bash
cd backend
conda env create -f environment.yml
conda activate dancer-backend
```

See [CONDA_SETUP.md](CONDA_SETUP.md) for detailed conda instructions.

### 2. Configure Environment Variables

Copy the example config file and fill in your AWS credentials:

```bash
cp config.env.example .env
```

Edit `.env` with your AWS credentials:
```
AWS_ACCESS_KEY_ID=your_actual_access_key
AWS_SECRET_ACCESS_KEY=your_actual_secret_key
AWS_REGION=us-east-1
S3_BUCKET=your-bucket-name
```

### 3. AWS S3 Setup

1. Create an S3 bucket in your AWS account
2. Configure bucket permissions for uploads
3. Create IAM user with S3 permissions:
   - `s3:PutObject`
   - `s3:GetObject` (optional, for download)
   - `s3:ListBucket` (optional)

### 4. Run the Server

```bash
python main.py
```

Or using uvicorn directly:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### `POST /upload`

Upload a video file with metadata.

**Parameters:**
- `file`: Video file (multipart/form-data)
- `user_id`: User identifier (string)
- `subject_id`: Subject identifier (string)  
- `activity`: Activity code (string)
- `shoe_type`: Type of shoes (string)
- `acq_datetime`: Date/time of acquisition (string)

**Response:**
```json
{
  "success": true,
  "upload_id": "uuid-string",
  "message": "File uploaded successfully"
}
```

### `GET /uploads/{upload_id}`

Get information about a specific upload.

### `GET /health`

Health check endpoint.

## Database Schema

The `uploads` table stores:
- `upload_id`: Unique identifier
- `user_id`: User who uploaded
- `subject_id`: Subject of the video
- `activity`: Activity code
- `shoe_type`: Shoe type
- `acq_datetime`: Acquisition date/time
- `filename`: Original filename
- `s3_key`: S3 object key
- `s3_bucket`: S3 bucket name
- `upload_timestamp`: When uploaded

## Development

### Running in Development Mode

```bash
uvicorn main:app --reload
```

### Testing the API

You can test the API using curl:

```bash
curl -X POST "http://localhost:8000/upload" \
  -H "accept: application/json" \
  -F "file=@test_video.mp4" \
  -F "user_id=test_user" \
  -F "subject_id=test_subject" \
  -F "activity=walking" \
  -F "shoe_type=sneakers" \
  -F "acq_datetime=2024-01-15T10:30:00"
```

## Production Deployment

For production:

1. Use PostgreSQL instead of SQLite
2. Set up proper AWS IAM roles
3. Use environment variables for all secrets
4. Deploy using Docker or cloud services
5. Configure proper CORS origins
6. Set up monitoring and logging

## Security Notes

- AWS credentials are stored server-side only
- File type validation prevents non-video uploads
- Database stores metadata for audit trails
- CORS is configured for specific origins only
