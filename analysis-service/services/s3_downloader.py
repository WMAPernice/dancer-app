"""
S3 File Downloader for processing uploaded videos
"""

import os
import logging
from typing import Optional, Dict, Any
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import aiofiles

logger = logging.getLogger(__name__)

class S3Downloader:
    """Handles downloading files from S3 for processing"""
    
    def __init__(self, config):
        self.config = config
        self.s3_client = None
        self._initialize_s3()
    
    def _initialize_s3(self):
        """Initialize S3 client"""
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.config.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=self.config.AWS_SECRET_ACCESS_KEY,
                region_name=self.config.AWS_REGION
            )
            
            # Test connection
            self._test_connection()
            logger.info("✓ S3 client initialized successfully")
            
        except NoCredentialsError:
            logger.error("❌ AWS credentials not found")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to initialize S3: {e}")
            raise
    
    def _test_connection(self):
        """Test S3 connection"""
        try:
            # Test with a simple list_objects_v2 call
            self.s3_client.list_objects_v2(
                Bucket=self.config.S3_BUCKET,
                Prefix=self.config.S3_PREFIX + "/",
                MaxKeys=1
            )
        except Exception as e:
            logger.warning(f"S3 connection test with list_objects_v2 failed: {e}")
            # Try alternative test method
            try:
                from urllib.parse import urlparse
                self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.config.S3_BUCKET, 'Key': f"{self.config.S3_PREFIX}/test"},
                    ExpiresIn=1
                )
                logger.info("S3 connection validated using presigned URL method")
            except Exception as e2:
                raise Exception(f"S3 connection test failed: {e2}")
    
    async def download_file(self, bucket: str, key: str, local_filename: Optional[str] = None) -> Optional[str]:
        """
        Download file from S3 to local storage
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            local_filename: Local filename (auto-generated if None)
            
        Returns:
            Path to downloaded file or None if failed
        """
        try:
            # Generate local filename if not provided
            if local_filename is None:
                # Extract filename from S3 key
                base_filename = os.path.basename(key)
                local_filename = os.path.join(self.config.DOWNLOAD_DIR, base_filename)
            
            # Ensure download directory exists
            os.makedirs(os.path.dirname(local_filename), exist_ok=True)
            
            logger.info(f"Downloading s3://{bucket}/{key} to {local_filename}")
            
            # Get object metadata first
            try:
                head_response = self.s3_client.head_object(Bucket=bucket, Key=key)
                file_size = head_response.get('ContentLength', 0)
                content_type = head_response.get('ContentType', 'unknown')
                
                logger.info(f"File size: {file_size} bytes, Content-Type: {content_type}")
                
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    logger.error(f"File not found: s3://{bucket}/{key}")
                    return None
                else:
                    logger.warning(f"Could not get file metadata: {e}")
            
            # Download the file
            self.s3_client.download_file(bucket, key, local_filename)
            
            # Verify download
            if os.path.exists(local_filename):
                downloaded_size = os.path.getsize(local_filename)
                logger.info(f"✓ Downloaded {downloaded_size} bytes to {local_filename}")
                return local_filename
            else:
                logger.error("Download completed but file not found locally")
                return None
                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                logger.error(f"Bucket not found: {bucket}")
            elif error_code == 'NoSuchKey':
                logger.error(f"File not found: s3://{bucket}/{key}")
            elif error_code == 'AccessDenied':
                logger.error(f"Access denied to s3://{bucket}/{key}")
            else:
                logger.error(f"S3 error downloading file: {e}")
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error downloading file: {e}")
            return None
    
    async def get_file_metadata(self, bucket: str, key: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for S3 object without downloading
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            
        Returns:
            Dictionary with file metadata or None if failed
        """
        try:
            response = self.s3_client.head_object(Bucket=bucket, Key=key)
            
            metadata = {
                'bucket': bucket,
                'key': key,
                'size': response.get('ContentLength', 0),
                'content_type': response.get('ContentType', 'unknown'),
                'last_modified': response.get('LastModified'),
                'etag': response.get('ETag', '').strip('"'),
                's3_metadata': response.get('Metadata', {}),
                'storage_class': response.get('StorageClass', 'STANDARD')
            }
            
            logger.info(f"Retrieved metadata for s3://{bucket}/{key}")
            return metadata
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                logger.error(f"File not found: s3://{bucket}/{key}")
            elif error_code == 'AccessDenied':
                logger.error(f"Access denied to s3://{bucket}/{key}")
            else:
                logger.error(f"S3 error getting metadata: {e}")
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error getting metadata: {e}")
            return None
    
    def cleanup_file(self, local_path: str) -> bool:
        """
        Clean up downloaded file
        
        Args:
            local_path: Path to local file to delete
            
        Returns:
            True if file was deleted successfully
        """
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
                logger.info(f"✓ Cleaned up file: {local_path}")
                return True
            else:
                logger.warning(f"File not found for cleanup: {local_path}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to cleanup file {local_path}: {e}")
            return False
    
    def get_download_stats(self) -> Dict[str, Any]:
        """Get download directory statistics"""
        try:
            download_dir = self.config.DOWNLOAD_DIR
            
            if not os.path.exists(download_dir):
                return {
                    'download_dir': download_dir,
                    'exists': False
                }
            
            # Count files and calculate total size
            file_count = 0
            total_size = 0
            
            for root, dirs, files in os.walk(download_dir):
                file_count += len(files)
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        total_size += os.path.getsize(file_path)
                    except OSError:
                        pass  # File might be in use or deleted
            
            return {
                'download_dir': download_dir,
                'exists': True,
                'file_count': file_count,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2)
            }
            
        except Exception as e:
            logger.error(f"Failed to get download stats: {e}")
            return {'error': str(e)}
