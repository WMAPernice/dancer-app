# DANCER Analysis Service

Standalone video processing service that polls SQS for upload notifications, downloads videos from S3, extracts metadata, and runs analysis scripts.

## 🏗️ Architecture

```
SQS Queue → Analysis Service → S3 Download → Metadata Extraction → Database Update
    ↑              ↓              ↓              ↓                    ↓
 Upload API    Long Polling   Video Files   Placeholder Script    Results
```

## 🚀 Quick Start

### 1. Install Dependencies

#### Option A: Using pip
```bash
cd analysis-service
pip install -r requirements.txt
```

#### Option B: Using Conda (Recommended)
```bash
# Create conda environment
conda create -n dancer-analysis python=3.9

# Activate environment
conda activate dancer-analysis

# Navigate to service directory
cd analysis-service

# Install dependencies
pip install -r requirements.txt
```

**Note**: You can use the same conda environment as the main backend (`dancer-backend`) or create a separate one for the analysis service.

### 2. Configure Environment

```bash
cp config.env.example .env
# Edit .env with your AWS credentials and configuration
```

### 3. Run the Service

```bash
python main.py
```

## ⚙️ Configuration

### Required Environment Variables

```bash
# AWS Credentials
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1

# SQS Queue (provide either URL or name)
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/account/queue-name
# OR
SQS_QUEUE_NAME=dancer-processing-queue

# S3 Configuration
S3_BUCKET=dancer-uploads
S3_PREFIX=uploads
```

### Optional Configuration

```bash
# Processing Settings
DOWNLOAD_DIR=./temp_downloads          # Where to download files
MAX_WORKERS=2                          # Future: parallel processing
CLEANUP_AFTER_PROCESSING=true         # Delete files after processing
SQS_WAIT_TIME=20                       # Long polling wait time (seconds)
SQS_VISIBILITY_TIMEOUT=300             # Message visibility timeout (seconds)

# Database
DATABASE_URL=sqlite:///./dancer_uploads.db  # Shared with main backend

# Logging
LOG_LEVEL=INFO
```

## 🔧 AWS Setup Requirements

### 1. SQS Queue Configuration

Create a queue with these settings:
- **Queue Name**: `dancer-processing-queue`
- **Visibility Timeout**: 300 seconds (5 minutes)
- **Message Retention**: 14 days
- **Receive Message Wait Time**: 20 seconds (long polling)
- **Dead Letter Queue**: Optional but recommended

### 2. S3 Event Notification

Configure S3 bucket to send notifications to SQS:

```json
{
  "Event": "s3:ObjectCreated:*",
  "Filter": {
    "Key": {
      "FilterRules": [
        {
          "Name": "prefix",
          "Value": "uploads/"
        }
      ]
    }
  },
  "Destination": {
    "SQSConfiguration": {
      "QueueArn": "arn:aws:sqs:region:account:dancer-processing-queue"
    }
  }
}
```

### 3. IAM Permissions

Analysis service needs these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes",
        "sqs:GetQueueUrl"
      ],
      "Resource": "arn:aws:sqs:region:account:dancer-processing-queue"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:GetObjectMetadata"
      ],
      "Resource": "arn:aws:s3:::dancer-uploads/uploads/*"
    }
  ]
}
```

## 📊 Service Components

### SQS Handler (`services/sqs_handler.py`)
- **Long polling** for cost-efficient message retrieval
- **Message parsing** for S3 event notifications
- **Error handling** with automatic message deletion for malformed messages

### S3 Downloader (`services/s3_downloader.py`)
- **Streaming downloads** for large video files
- **Metadata extraction** from S3 objects
- **Automatic cleanup** of temporary files

### Metadata Extractor (`services/metadata_extractor.py`)
- **Video metadata extraction** using ffprobe (if available)
- **Fallback analysis** for basic file information
- **Placeholder analysis script** for gait analysis simulation

### Database Updater (`services/database_updater.py`)
- **Processing status tracking** in shared database
- **Results storage** as JSON metadata
- **Retry handling** for failed processing attempts

## 🎬 Message Processing Flow

1. **Poll SQS** for new upload notifications (20-second long polling)
2. **Parse message** to extract S3 bucket and key information
3. **Create processing record** in database with "processing" status
4. **Download file** from S3 to local temporary storage
5. **Extract metadata** using ffprobe or fallback analysis
6. **Run analysis script** (currently placeholder gait analysis)
7. **Update database** with results and "completed" status
8. **Cleanup files** (if configured)
9. **Delete SQS message** to mark as processed

## 📈 Monitoring & Health Checks

### Service Statistics
The service tracks and displays:
- Messages processed
- Files downloaded
- Processing errors
- Queue statistics
- Download directory usage

### Health Check Function
```python
import asyncio
from main import health_check

# Check service health
result = asyncio.run(health_check())
print(result)
```

### Log Files
- Console output for real-time monitoring
- `analysis_service.log` file for persistent logging

## 🛠️ Development & Testing

### Running with Test Messages

```python
# Send test message to SQS
from services.sqs_handler import SQSHandler
from config import Config

sqs = SQSHandler(Config)
await sqs.send_test_message("dancer-uploads", "uploads/test/video.mp4")
```

### Local Development
1. Use LocalStack for AWS services simulation
2. Configure `.env` with LocalStack endpoints
3. Run service with `LOG_LEVEL=DEBUG` for detailed logging

### Placeholder Analysis Script
Current implementation includes a placeholder that:
- Simulates gait analysis processing
- Extracts basic video metadata
- Provides example results structure
- **Replace with actual analysis algorithms**

## 🔄 Production Deployment

### Docker Deployment
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "main.py"]
```

### Kubernetes Deployment
- Deploy as a Deployment with configurable replicas
- Use ConfigMaps for environment variables
- Use Secrets for AWS credentials
- Set up health check probes

### Scaling Considerations
- **Horizontal scaling**: Run multiple instances
- **Queue partitioning**: Use multiple SQS queues
- **Resource allocation**: CPU/memory based on video file sizes
- **Storage management**: Ensure adequate disk space for downloads

## 🚨 Error Handling

### Automatic Retries
- Failed messages are marked in database with retry count
- SQS visibility timeout allows automatic retry
- Dead letter queue for permanently failed messages

### Common Issues
1. **S3 Access Denied**: Check IAM permissions
2. **SQS Connection Failed**: Verify queue URL and credentials
3. **Download Failures**: Check network connectivity and disk space
4. **Processing Timeouts**: Increase SQS visibility timeout

## 🎯 Next Steps

1. **Replace placeholder analysis** with actual gait analysis algorithms
2. **Add video preprocessing** (format conversion, quality checks)
3. **Implement parallel processing** for multiple workers
4. **Add result visualization** and reporting features
5. **Integrate with clinical workflows** and assessment tools

The service is designed to be modular and extensible - replace the placeholder components with your actual analysis pipeline!
