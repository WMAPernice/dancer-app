# SQS Configuration Parameters - Detailed Usage

This document explains how the three key SQS configuration parameters (`SQS_VISIBILITY_TIMEOUT`, `SQS_WAIT_TIME`, and `SQS_MAX_MESSAGES`) are used throughout the analysis-service modules.

## Configuration Parameters Overview

### 1. `SQS_WAIT_TIME` (Default: 20 seconds)
**Purpose**: Controls long polling wait time for cost-efficient message retrieval.

### 2. `SQS_VISIBILITY_TIMEOUT` (Default: 300 seconds / 5 minutes)  
**Purpose**: Controls how long messages remain invisible to other consumers after being retrieved.

### 3. `SQS_MAX_MESSAGES` (Default: 10 messages)
**Purpose**: Maximum number of messages that can be retrieved in a single poll operation.

---

## How Each Parameter Is Used

### 🕐 `SQS_WAIT_TIME` - Long Polling Configuration

**Used in**: `services/sqs_handler.py` → `poll_messages()` method

```python
response = self.sqs_client.receive_message(
    QueueUrl=self.queue_url,
    MaxNumberOfMessages=max_messages,
    WaitTimeSeconds=self.config.SQS_WAIT_TIME,  # ← Used here
    VisibilityTimeoutSeconds=self.config.SQS_VISIBILITY_TIMEOUT,
    MessageAttributeNames=['All']
)
```

**What it does**:
- **Long Polling**: When `SQS_WAIT_TIME > 0`, SQS will wait up to this many seconds for messages to arrive before returning an empty response
- **Cost Efficiency**: Reduces the number of empty `ReceiveMessage` API calls
- **Recommended**: 20 seconds (maximum allowed by AWS)

**Impact**:
- ✅ **Higher values (15-20)**: More cost-efficient, fewer API calls
- ❌ **Lower values (0-5)**: More expensive, frequent polling
- ⚠️ **Value of 0**: Disables long polling (not recommended)

---

### 🔒 `SQS_VISIBILITY_TIMEOUT` - Message Processing Time Override

**Used in**: `services/sqs_handler.py` → `poll_messages()` method

```python
response = self.sqs_client.receive_message(
    QueueUrl=self.queue_url,
    MaxNumberOfMessages=max_messages,
    WaitTimeSeconds=self.config.SQS_WAIT_TIME,
    VisibilityTimeoutSeconds=self.config.SQS_VISIBILITY_TIMEOUT,  # ← Overrides queue default
    MessageAttributeNames=['All']
)
```

**What it does**:
- **Per-Request Override**: Overrides the queue's default visibility timeout for this specific receive operation
- **Queue Default**: SQS queues have their own default visibility timeout (often 30 seconds)
- **Dynamic Control**: Allows different processing timeouts based on workload requirements
- **Message Locking**: Once retrieved, messages become invisible to other consumers for this duration
- **Processing Window**: Gives the analysis service time to download, process, and delete the message
- **Failure Recovery**: If processing fails, the message becomes visible again after timeout

**Queue-Level vs Request-Level**:
```
┌─────────────────────┬─────────────────────┬──────────────────┐
│ Queue Default       │ Request Override    │ Actual Timeout   │
├─────────────────────┼─────────────────────┼──────────────────┤
│ 30 seconds          │ 300 seconds         │ 300 seconds ✅   │
│ 600 seconds         │ 300 seconds         │ 300 seconds ✅   │
│ Not specified       │ 300 seconds         │ 300 seconds ✅   │
└─────────────────────┴─────────────────────┴──────────────────┘
```

**Our Processing Pipeline Duration**:
```
┌─────────────────┬──────────────────┬─────────────────┐
│ Download Video  │ Extract Metadata │ Update Database │
│ (30-120 sec)    │ (5-30 sec)      │ (1-5 sec)      │
└─────────────────┴──────────────────┴─────────────────┘
                Total: ~40-155 seconds
```

**Recommended Values**:
- ✅ **300 seconds (5 min)**: Safe buffer for large video files
- ⚠️ **180 seconds (3 min)**: Minimum for most video processing
- ❌ **60 seconds (1 min)**: Too short, may cause duplicate processing

---

### 📊 `SQS_MAX_MESSAGES` - Batch Processing Control

**Currently NOT used directly** - There's a discrepancy in the implementation!

**Expected usage** (should be in `main.py`):
```python
# Currently hardcoded:
messages = await self.sqs_handler.poll_messages(max_messages=5)

# Should use config:
messages = await self.sqs_handler.poll_messages(max_messages=self.config.SQS_MAX_MESSAGES)
```

**What it should control**:
- **Batch Size**: How many messages to process in parallel
- **Throughput**: Higher values = more concurrent processing
- **Memory Usage**: Higher values = more simultaneous video downloads

**Recommended Values**:
- ✅ **5-10 messages**: Good balance for video processing
- ⚠️ **1-3 messages**: Conservative, lower throughput
- ❌ **10+ messages**: May overwhelm system with large video files

---

## Current Implementation Issues

### 🚨 Issue 1: `SQS_MAX_MESSAGES` Not Used
**Problem**: `main.py` hardcodes `max_messages=5` instead of using `self.config.SQS_MAX_MESSAGES`

**Location**: `analysis-service/main.py:116`
```python
# Current (incorrect):
messages = await self.sqs_handler.poll_messages(max_messages=5)

# Should be:
messages = await self.sqs_handler.poll_messages(max_messages=self.config.SQS_MAX_MESSAGES)
```

### 💡 Design Decision: Per-Request vs Queue-Level Timeout
**Current Approach**: Using `VisibilityTimeoutSeconds` in `receive_message()` calls

**Why This Works**:
- ✅ **Flexibility**: Can adjust timeout based on current workload
- ✅ **Override Control**: Overrides any queue default (whether 30s or 600s)
- ✅ **Consistent Behavior**: Same timeout regardless of queue configuration
- ✅ **Dynamic Adaptation**: Could implement adaptive timeouts based on file size

**Alternative Approach**: Set queue-level default:
```bash
# Option: Configure queue with default timeout
aws sqs create-queue \
  --queue-name dancer-upload-notifications \
  --attributes '{
    "VisibilityTimeoutSeconds": "300",
    "ReceiveMessageWaitTimeSeconds": "20"
  }'
```

**Recommendation**: Current approach is correct for microservices that need control over processing timeouts

### 🤔 When to Use Each Approach

#### **Use Request-Level Override (Current)** ✅
- ✅ **Microservices**: Different services process same queue with different timeouts
- ✅ **Variable Processing**: Video files vary greatly in size/complexity
- ✅ **Dynamic Adaptation**: Want to adjust timeout based on file metadata
- ✅ **Multi-Consumer**: Different consumers with different processing speeds
- ✅ **Development Flexibility**: Easy to change timeout without AWS console

#### **Use Queue-Level Default** 
- ✅ **Single Consumer**: Only one service processes the queue
- ✅ **Uniform Processing**: All messages take similar time to process
- ✅ **Set-and-Forget**: Don't need dynamic timeout adjustment
- ✅ **Infrastructure as Code**: Want all settings defined in AWS resources

#### **Hybrid Approach** ⭐ **Best Practice**
```bash
# Set reasonable queue default for fallback
aws sqs create-queue \
  --queue-name dancer-upload-notifications \
  --attributes '{
    "VisibilityTimeoutSeconds": "180",
    "ReceiveMessageWaitTimeSeconds": "20"
  }'

# Plus use request-level override for dynamic control
VisibilityTimeoutSeconds=self.calculate_timeout(file_size)
```

---

## Configuration Recommendations

### For Development
```bash
SQS_WAIT_TIME=20                    # Full long polling
SQS_VISIBILITY_TIMEOUT=300          # 5 minutes processing window
SQS_MAX_MESSAGES=3                  # Conservative batch size
```

### For Production
```bash
SQS_WAIT_TIME=20                    # Full long polling
SQS_VISIBILITY_TIMEOUT=600          # 10 minutes for large files
SQS_MAX_MESSAGES=5                  # Balanced throughput
```

### For High Throughput
```bash
SQS_WAIT_TIME=20                    # Full long polling
SQS_VISIBILITY_TIMEOUT=300          # Standard processing window
SQS_MAX_MESSAGES=10                 # Higher batch processing
```

---

## Performance Impact Analysis

### Long Polling (`SQS_WAIT_TIME`)
```
Short Polling (0s):     ~3600 API calls/hour = $1.80/hour
Long Polling (20s):     ~180 API calls/hour = $0.09/hour
                        💰 Savings: ~95% cost reduction
```

### Visibility Timeout (`SQS_VISIBILITY_TIMEOUT`)
```
Too Short (60s):       Risk of duplicate processing
Optimal (300s):        Safe processing window
Too Long (900s):       Slow error recovery
```

### Batch Size (`SQS_MAX_MESSAGES`)
```
Small Batch (1-3):     Lower memory, slower throughput
Medium Batch (5-7):    Balanced performance
Large Batch (8-10):    Higher throughput, more memory
```

---

## Monitoring Recommendations

### CloudWatch Metrics to Track
1. **ApproximateNumberOfMessages**: Queue backlog
2. **ApproximateNumberOfMessagesNotVisible**: Messages being processed
3. **NumberOfMessagesReceived**: Processing rate
4. **ApproximateAgeOfOldestMessage**: Processing delay

### Alerts to Set
- Queue depth > 50 messages (processing lag)
- Messages not visible > visibility timeout (processing failures)
- No messages received for > 1 hour (service down)

---

## Next Steps

1. **Fix `SQS_MAX_MESSAGES` usage** in `main.py`
2. **Add queue-level configuration** in setup scripts
3. **Implement adaptive batching** based on system load
4. **Add CloudWatch monitoring** for performance tracking
