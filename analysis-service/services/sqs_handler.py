"""
SQS Message Handler for processing video upload notifications
"""

import json
import asyncio
import logging
from typing import List, Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)

class SQSHandler:
    """Handles SQS message polling and processing"""
    
    def __init__(self, config):
        self.config = config
        self.sqs_client = None
        self.queue_url = None
        self._initialize_sqs()
    
    def _initialize_sqs(self):
        """Initialize SQS client and get queue URL"""
        try:
            # Initialize SQS client
            self.sqs_client = boto3.client(
                'sqs',
                aws_access_key_id=self.config.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=self.config.AWS_SECRET_ACCESS_KEY,
                region_name=self.config.AWS_REGION
            )
            
            # Get queue URL
            if self.config.SQS_QUEUE_URL:
                self.queue_url = self.config.SQS_QUEUE_URL
                logger.info(f"Using provided queue URL: {self.queue_url}")
            else:
                # Get queue URL by name
                response = self.sqs_client.get_queue_url(
                    QueueName=self.config.SQS_QUEUE_NAME
                )
                self.queue_url = response['QueueUrl']
                logger.info(f"Found queue URL: {self.queue_url}")
            
            # Test connection
            self._test_connection()
            logger.info("✓ SQS client initialized successfully")
            
        except NoCredentialsError:
            logger.error("❌ AWS credentials not found")
            raise
        except ClientError as e:
            logger.error(f"❌ Failed to initialize SQS: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error initializing SQS: {e}")
            raise
    
    def _test_connection(self):
        """Test SQS connection by getting queue attributes"""
        try:
            self.sqs_client.get_queue_attributes(
                QueueUrl=self.queue_url,
                AttributeNames=['QueueArn']
            )
        except Exception as e:
            raise Exception(f"SQS connection test failed: {e}")
    
    async def poll_messages(self, max_messages: int = None) -> List[Dict[str, Any]]:
        """
        Poll SQS for new messages using long polling
        
        Args:
            max_messages: Maximum number of messages to retrieve
            
        Returns:
            List of message dictionaries
        """
        # Use config default if not specified
        if max_messages is None:
            max_messages = self.config.SQS_MAX_MESSAGES
            
        try:
            # Use long polling for cost efficiency
            response = self.sqs_client.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=self.config.SQS_WAIT_TIME,
                VisibilityTimeout=self.config.SQS_VISIBILITY_TIMEOUT,
                MessageAttributeNames=['All']
            )
            
            messages = response.get('Messages', [])
            logger.info(f"Received {len(messages)} messages from SQS")
            
            # Parse messages and extract S3 event information
            parsed_messages = []
            for message in messages:
                try:
                    parsed_message = self._parse_message(message)
                    if parsed_message:
                        parsed_messages.append(parsed_message)
                except Exception as e:
                    logger.error(f"Failed to parse message: {e}")
                    # Delete malformed messages
                    await self.delete_message(message)
            
            return parsed_messages
            
        except Exception as e:
            logger.error(f"Error polling SQS: {e}")
            return []
    
    def _parse_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse SQS message to extract S3 event information
        
        Args:
            message: Raw SQS message
            
        Returns:
            Parsed message with S3 object information
        """
        try:
            # Parse message body (usually contains S3 event notification)
            body = json.loads(message['Body'])
            
            # Handle S3 event notification format
            if 'Records' in body:
                for record in body['Records']:
                    # Validate event source matches expected (aws:s3)
                    event_source = record.get('eventSource', '')
                    if event_source != self.config.EXPECTED_S3_EVENT_SOURCE:
                        logger.warning(f"Unexpected event source: {event_source}, expected: {self.config.EXPECTED_S3_EVENT_SOURCE}")
                        continue
                    
                    # Validate event name is ObjectCreated event
                    event_name = record.get('eventName', '')
                    if not event_name.startswith(self.config.EXPECTED_S3_EVENT_PREFIX):
                        logger.warning(f"Unexpected event type: {event_name}, expected prefix: {self.config.EXPECTED_S3_EVENT_PREFIX}")
                        continue
                    
                    s3_info = record['s3']
                    bucket_name = s3_info['bucket']['name']
                    object_key = s3_info['object']['key']
                    
                    # Validate bucket matches expected bucket
                    if bucket_name != self.config.S3_BUCKET:
                        logger.warning(f"Unexpected bucket: {bucket_name}, expected: {self.config.S3_BUCKET}")
                        continue
                    
                    # Validate object is in expected prefix
                    if not object_key.startswith(self.config.S3_PREFIX + '/'):
                        logger.warning(f"Object not in expected prefix: {object_key}, expected prefix: {self.config.S3_PREFIX}/")
                        continue
                    
                    logger.info(f"✅ Valid S3 event: {event_name} for s3://{bucket_name}/{object_key}")
                    
                    return {
                        'message_id': message['MessageId'],
                        'receipt_handle': message['ReceiptHandle'],
                        'bucket': bucket_name,
                        'key': object_key,
                        'size': s3_info['object'].get('size', 0),
                        'etag': s3_info['object'].get('eTag', ''),
                        'event_name': event_name,
                        'event_time': record.get('eventTime'),
                        'event_source': event_source,
                        'aws_region': record.get('awsRegion'),
                        'raw_message': message
                    }
            
            # Handle direct message format (for testing)
            elif 'bucket' in body and 'key' in body:
                return {
                    'message_id': message['MessageId'],
                    'receipt_handle': message['ReceiptHandle'],
                    'bucket': body['bucket'],
                    'key': body['key'],
                    'size': body.get('size', 0),
                    'event_name': 'manual',
                    'event_time': None,
                    'raw_message': message
                }
            
            else:
                logger.warning(f"Unknown message format: {body}")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing message: {e}")
            return None
    
    async def delete_message(self, message: Dict[str, Any]):
        """
        Delete processed message from SQS
        
        Args:
            message: Message to delete (can be raw message or parsed message)
        """
        try:
            # Handle both raw messages and parsed messages
            if 'receipt_handle' in message:
                receipt_handle = message['receipt_handle']
            elif 'ReceiptHandle' in message:
                receipt_handle = message['ReceiptHandle']
            else:
                logger.error("No receipt handle found in message")
                return
            
            self.sqs_client.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle
            )
            logger.info(f"✓ Deleted message from SQS")
            
        except Exception as e:
            logger.error(f"Failed to delete message: {e}")
    
    async def send_test_message(self, bucket: str, key: str) -> bool:
        """
        Send a test message to SQS (useful for testing)
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            
        Returns:
            True if message sent successfully
        """
        try:
            test_message = {
                "bucket": bucket,
                "key": key,
                "size": 1000,
                "test": True
            }
            
            self.sqs_client.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(test_message)
            )
            
            logger.info(f"✓ Sent test message for {bucket}/{key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send test message: {e}")
            return False
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        try:
            response = self.sqs_client.get_queue_attributes(
                QueueUrl=self.queue_url,
                AttributeNames=['All']
            )
            
            attributes = response['Attributes']
            return {
                'queue_url': self.queue_url,
                'approximate_messages': int(attributes.get('ApproximateNumberOfMessages', 0)),
                'messages_in_flight': int(attributes.get('ApproximateNumberOfMessagesNotVisible', 0)),
                'messages_delayed': int(attributes.get('ApproximateNumberOfMessagesDelayed', 0))
            }
            
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {}
