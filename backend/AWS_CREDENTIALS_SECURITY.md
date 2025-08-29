# AWS Credentials Security in DANCER Backend

## Problem: Boto3 Credential Chain Issues

### Default Boto3 Behavior
Boto3 searches for credentials in this order:
1. **Explicit parameters** (what we want)
2. **Environment variables** 
3. **~/.aws/credentials** (security risk!)
4. **~/.aws/config** (security risk!)
5. **IAM roles** (EC2/ECS only)
6. **STS tokens**

### Security Risks
- **Credential confusion**: Using wrong AWS account
- **Silent fallbacks**: App works with wrong credentials
- **Development leaks**: Personal AWS credentials used in production
- **Audit problems**: Unclear which credentials are being used

## Our Solution: Explicit Credential Control

### 1. Explicit Validation
```python
def initialize_s3_client():
    # Fail fast if credentials not provided via .env
    if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
        logger.error("AWS credentials not provided via environment variables")
        return None
```

### 2. Credential Testing
```python
# Test credentials immediately on startup
client.list_buckets()  # Fails fast if invalid
```

### 3. Environment Cleanup
```python
# Remove credentials from environment after loading
del os.environ["AWS_ACCESS_KEY_ID"]
del os.environ["AWS_SECRET_ACCESS_KEY"]
```

### 4. Detailed Health Monitoring
```python
# /health endpoint shows credential status
{
  "s3": {
    "status": "connected",
    "details": {"bucket": "dancer-uploads", "region": "us-east-1"}
  },
  "environment": {
    "has_aws_access_key": true,
    "has_aws_secret_key": true
  }
}
```

## Benefits

### ✅ Security Improvements
- **No credential fallback** to local files
- **Explicit credential source** (only .env file)
- **Early failure detection** (startup validation)
- **Credential isolation** (removed from environment)

### ✅ Operational Benefits
- **Clear error messages** when credentials missing
- **Health check visibility** into S3 configuration
- **Consistent behavior** across environments
- **Audit trail** of credential usage

## Usage Guide

### 1. Required .env Configuration
```bash
# These MUST be provided - no fallbacks allowed
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=us-east-1
S3_BUCKET=your-bucket-name
```

### 2. Startup Behavior
```bash
# With valid credentials:
INFO:S3 client initialized successfully with provided credentials
INFO:Using AWS region: us-east-1

# With missing credentials:
ERROR:AWS credentials not provided via environment variables
ERROR:Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in your .env file

# With invalid credentials:
ERROR:S3 credentials validation failed: The AWS Access Key Id you provided does not exist
ERROR:Please check your AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
```

### 3. Health Check Monitoring
```bash
# Check S3 status
curl http://localhost:8000/health

# Response shows credential status
{
  "status": "healthy",
  "s3": {
    "status": "connected",        # or "not_configured" / "connection_failed"
    "details": {
      "bucket": "dancer-uploads",
      "region": "us-east-1",
      "prefix": "uploads"
    }
  }
}
```

## Troubleshooting

### Issue: "S3 client not initialized"
**Cause**: Missing AWS credentials in .env file
**Solution**: 
```bash
# Add to .env file:
AWS_ACCESS_KEY_ID=your_key_here
AWS_SECRET_ACCESS_KEY=your_secret_here
```

### Issue: "S3 credentials validation failed"
**Cause**: Invalid AWS credentials
**Solution**: 
1. Verify credentials in AWS Console
2. Check IAM user has S3 permissions
3. Ensure no typos in .env file

### Issue: "Connection failed" in health check
**Cause**: Network or bucket permission issues
**Solution**:
1. Check bucket exists and is accessible
2. Verify IAM permissions include s3:ListBucket
3. Check network connectivity to AWS

## Production Deployment

### Environment Variable Security
```bash
# Production: Use secure secret management
AWS_ACCESS_KEY_ID=${SECRET_AWS_ACCESS_KEY}
AWS_SECRET_ACCESS_KEY=${SECRET_AWS_SECRET_KEY}

# Never commit real credentials to git
```

### IAM Best Practices
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::dancer-uploads",
        "arn:aws:s3:::dancer-uploads/*"
      ]
    }
  ]
}
```

### Monitoring in Production
- Monitor `/health` endpoint for S3 connectivity
- Alert on S3 credential failures
- Regular credential rotation
- Audit S3 access logs

This approach ensures that DANCER only uses explicitly provided credentials and fails safely when they're not available!
