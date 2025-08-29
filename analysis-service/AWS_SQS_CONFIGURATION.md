# AWS SQS Configuration for S3 Event Notifications

This document explains how to configure AWS SQS to receive S3 event notifications for the DANCER analysis service.

## Overview

When a file is uploaded to S3, we want S3 to automatically send a notification message to an SQS queue. Our analysis service then polls this queue to process new uploads.

## Required AWS Configuration

### 1. SQS Queue Access Policy

The SQS queue **must** have an access policy that allows S3 to send messages. Here's the required policy:

```json
{
  "Version": "2012-10-17",
  "Id": "allow-s3-to-send-messages",
  "Statement": [
    {
      "Sid": "AllowS3ToSendMessages",
      "Effect": "Allow",
      "Principal": {
        "Service": "s3.amazonaws.com"
      },
      "Action": "SQS:SendMessage",
      "Resource": "arn:aws:sqs:REGION:ACCOUNT-ID:QUEUE-NAME",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "YOUR-AWS-ACCOUNT-ID"
        },
        "ArnLike": {
          "aws:SourceArn": "arn:aws:s3:::YOUR-BUCKET-NAME"
        }
      }
    }
  ]
}
```

**Replace the following values:**
- `REGION`: Your AWS region (e.g., `us-east-1`)
- `ACCOUNT-ID`: Your AWS account ID
- `QUEUE-NAME`: Your SQS queue name (e.g., `dancer-upload-notifications`)
- `YOUR-AWS-ACCOUNT-ID`: Your AWS account ID (same as above)
- `YOUR-BUCKET-NAME`: Your S3 bucket name (e.g., `dancer-uploads`)

### 2. S3 Event Notification Configuration

Configure your S3 bucket to send notifications to the SQS queue:

```json
{
  "QueueConfigurations": [
    {
      "Id": "UploadNotification",
      "QueueArn": "arn:aws:sqs:REGION:ACCOUNT-ID:QUEUE-NAME",
      "Events": [
        "s3:ObjectCreated:*"
      ],
      "Filter": {
        "Key": {
          "FilterRules": [
            {
              "Name": "prefix",
              "Value": "uploads/"
            },
            {
              "Name": "suffix",
              "Value": ".mp4"
            }
          ]
        }
      }
    }
  ]
}
```

## Step-by-Step Setup

### Step 1: Create SQS Queue

```bash
# Create the SQS queue
aws sqs create-queue \
  --queue-name dancer-upload-notifications \
  --attributes '{
    "DelaySeconds": "0",
    "MaxReceiveCount": "3",
    "MessageRetentionPeriod": "1209600",
    "ReceiveMessageWaitTimeSeconds": "20",
    "VisibilityTimeoutSeconds": "300"
  }'
```

### Step 2: Set SQS Queue Policy

```bash
# Set the queue policy to allow S3 to send messages
aws sqs set-queue-attributes \
  --queue-url https://sqs.REGION.amazonaws.com/ACCOUNT-ID/dancer-upload-notifications \
  --attributes '{
    "Policy": "{\"Version\":\"2012-10-17\",\"Id\":\"allow-s3-to-send-messages\",\"Statement\":[{\"Sid\":\"AllowS3ToSendMessages\",\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"s3.amazonaws.com\"},\"Action\":\"SQS:SendMessage\",\"Resource\":\"arn:aws:sqs:REGION:ACCOUNT-ID:dancer-upload-notifications\",\"Condition\":{\"StringEquals\":{\"aws:SourceAccount\":\"ACCOUNT-ID\"},\"ArnLike\":{\"aws:SourceArn\":\"arn:aws:s3:::dancer-uploads\"}}}]}"
  }'
```

### Step 3: Configure S3 Bucket Notifications

```bash
# Create notification configuration file
cat > notification-config.json << EOF
{
  "QueueConfigurations": [
    {
      "Id": "UploadNotification",
      "QueueArn": "arn:aws:sqs:REGION:ACCOUNT-ID:dancer-upload-notifications",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": {
        "Key": {
          "FilterRules": [
            {
              "Name": "prefix",
              "Value": "uploads/"
            },
            {
              "Name": "suffix", 
              "Value": ".mp4"
            }
          ]
        }
      }
    }
  ]
}
EOF

# Apply notification configuration to S3 bucket
aws s3api put-bucket-notification-configuration \
  --bucket dancer-uploads \
  --notification-configuration file://notification-config.json
```

## Message Format

When S3 sends a notification to SQS, the message will look like this:

```json
{
  "Records": [
    {
      "eventVersion": "2.1",
      "eventSource": "aws:s3",
      "awsRegion": "us-east-1",
      "eventTime": "2024-01-15T10:30:00.000Z",
      "eventName": "ObjectCreated:Put",
      "userIdentity": {
        "principalId": "AIDACKCEVSQ6C2EXAMPLE"
      },
      "requestParameters": {
        "sourceIPAddress": "203.0.113.1"
      },
      "responseElements": {
        "x-amz-request-id": "C3D13FE58DE4C810",
        "x-amz-id-2": "FMyUVURIY8/IgAtTv8xRjskZQpcIZ9KG4V5Wp6S7S/JRWeUWerMUE5JgHvANOjpD"
      },
      "s3": {
        "s3SchemaVersion": "1.0",
        "configurationId": "UploadNotification",
        "bucket": {
          "name": "dancer-uploads",
          "ownerIdentity": {
            "principalId": "A3NL1KOZZKExample"
          },
          "arn": "arn:aws:s3:::dancer-uploads"
        },
        "object": {
          "key": "uploads/user123/subject456/20240115_103000_gait.mp4",
          "size": 15728640,
          "eTag": "0123456789abcdef0123456789abcdef",
          "sequencer": "0A1B2C3D4E5F678901"
        }
      }
    }
  ]
}
```

## Security Considerations

### 1. Principle of Least Privilege

The SQS policy should:
- Only allow the specific S3 service principal
- Only allow `sqs:SendMessage` action (not other SQS operations)
- Include source account and source ARN conditions
- Restrict to your specific bucket

### 2. Source Validation

Always include these conditions in your SQS policy:

```json
"Condition": {
  "StringEquals": {
    "aws:SourceAccount": "YOUR-AWS-ACCOUNT-ID"
  },
  "StringLike": {
    "aws:SourceArn": "arn:aws:s3:::YOUR-BUCKET-NAME/*"
  }
}
```

### 3. Queue Attributes

Recommended SQS queue settings:

- **VisibilityTimeoutSeconds**: `300` (5 minutes) - time for processing
- **MessageRetentionPeriod**: `1209600` (14 days) - keep messages for 2 weeks
- **ReceiveMessageWaitTimeSeconds**: `20` - enable long polling
- **MaxReceiveCount**: `3` - retry failed messages 3 times before DLQ

## Testing the Configuration

### 1. Test S3 to SQS Delivery

```bash
# Upload a test file to trigger notification
aws s3 cp test-video.mp4 s3://dancer-uploads/uploads/test/

# Check if message appears in queue
aws sqs receive-message \
  --queue-url https://sqs.REGION.amazonaws.com/ACCOUNT-ID/dancer-upload-notifications \
  --wait-time-seconds 20
```

### 2. Test Analysis Service

```bash
# Run the analysis service to process the message
cd analysis-service
python main.py
```

## Troubleshooting

### Common Issues

1. **No messages in queue after S3 upload**
   - Check SQS access policy has correct principal (`s3.amazonaws.com`)
   - Verify S3 notification configuration points to correct queue ARN
   - Ensure bucket name and queue ARN match in both configurations

2. **Access denied errors**
   - Verify aws:SourceAccount condition matches your account ID
   - Check aws:SourceArn condition includes your bucket name
   - Ensure queue ARN is correct in S3 notification config

3. **Messages not being processed**
   - Check analysis service has SQS permissions (sqs:ReceiveMessage, sqs:DeleteMessage)
   - Verify queue URL in analysis service configuration
   - Check CloudWatch logs for detailed error messages

### Debug Commands

```bash
# Check SQS queue attributes
aws sqs get-queue-attributes \
  --queue-url https://sqs.REGION.amazonaws.com/ACCOUNT-ID/dancer-upload-notifications \
  --attribute-names All

# Check S3 notification configuration
aws s3api get-bucket-notification-configuration \
  --bucket dancer-uploads

# Check queue policy
aws sqs get-queue-attributes \
  --queue-url https://sqs.REGION.amazonaws.com/ACCOUNT-ID/dancer-upload-notifications \
  --attribute-names Policy
```

## Environment Variables

Update your `analysis-service/config.env.example`:

```bash
# SQS Configuration
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/123456789012/dancer-upload-notifications
SQS_REGION=us-east-1
SQS_LONG_POLL_TIMEOUT=20
SQS_VISIBILITY_TIMEOUT=300
SQS_MAX_MESSAGES=10

# Expected S3 notification format
EXPECTED_S3_EVENT_SOURCE=aws:s3
EXPECTED_S3_EVENT_PREFIX=ObjectCreated
```

## Next Steps

1. **Set up Dead Letter Queue (DLQ)** for failed message processing
2. **Configure CloudWatch alarms** for queue depth monitoring
3. **Set up cross-region replication** if needed for disaster recovery
4. **Implement message deduplication** if using FIFO queues

---

**Important**: The principal `s3.amazonaws.com` and action `sqs:SendMessage` are **required** for S3-to-SQS integration to work. Without this policy, S3 cannot deliver notifications to your queue.
