"""
DANCER Analysis Service - Standalone video processing service

This service polls SQS for upload notifications, downloads videos from S3,
extracts metadata, and runs analysis scripts.
"""

import asyncio
import logging
import signal
import sys
import io
from datetime import datetime
from typing import Dict, Any

# Local imports
from config import Config
from services.sqs_handler import SQSHandler
from services.s3_downloader import S3Downloader
from services.metadata_extractor import MetadataExtractor
from services.database_updater import DatabaseUpdater

# Configure logging with UTF-8 encoding for Windows compatibility
# Use UTF-8 wrapper for stdout on Windows to handle emoji characters
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('analysis_service.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

class AnalysisService:
    """Main analysis service orchestrator"""
    
    def __init__(self):
        self.config = Config
        self.running = False
        
        # Initialize services
        self.sqs_handler = None
        self.s3_downloader = None
        self.metadata_extractor = None
        self.database_updater = None
        
        # Statistics
        self.stats = {
            'start_time': datetime.utcnow(),
            'messages_processed': 0,
            'files_downloaded': 0,
            'processing_errors': 0,
            'last_activity': None
        }
        
        # Runtime limit
        self.max_runtime_seconds = self.config.MAX_RUNTIME_HOURS * 3600 if self.config.MAX_RUNTIME_HOURS > 0 else None
    
    async def initialize(self):
        """Initialize all service components"""
        try:
            logger.info("🚀 Initializing DANCER Analysis Service...")
            
            # Validate configuration
            self.config.validate()
            self.config.print_config()
            
            # Initialize service components
            logger.info("📡 Initializing SQS handler...")
            self.sqs_handler = SQSHandler(self.config)
            
            logger.info("📦 Initializing S3 downloader...")
            self.s3_downloader = S3Downloader(self.config)
            
            logger.info("🔍 Initializing metadata extractor...")
            self.metadata_extractor = MetadataExtractor(self.config)
            
            logger.info("💾 Initializing database updater...")
            self.database_updater = DatabaseUpdater(self.config)
            
            logger.info("✓ All services initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize services: {e}")
            return False
    
    async def start(self):
        """Start the analysis service"""
        if not await self.initialize():
            logger.error("Failed to initialize services. Exiting.")
            return
        
        self.running = True
        logger.info("🎬 Starting analysis service main loop...")
        
        # Print initial statistics
        await self.print_stats()
        
        try:
            while self.running:
                # Check runtime limit
                if self.max_runtime_seconds:
                    elapsed_seconds = (datetime.utcnow() - self.stats['start_time']).total_seconds()
                    if elapsed_seconds >= self.max_runtime_seconds:
                        logger.info(f"⏰ Reached maximum runtime limit of {self.config.MAX_RUNTIME_HOURS} hours. Shutting down...")
                        break
                
                await self.process_cycle()
                
                # Brief pause between cycles to prevent excessive polling
                if self.running:
                    await asyncio.sleep(self.config.POLL_INTERVAL_SECONDS)
                    
        except KeyboardInterrupt:
            logger.info("⏹️  Received shutdown signal")
        except Exception as e:
            logger.error(f"❌ Unexpected error in main loop: {e}")
        finally:
            await self.shutdown()
    
    async def process_cycle(self):
        """Single processing cycle - poll SQS and process messages"""
        try:
            # Poll for messages
            messages = await self.sqs_handler.poll_messages(max_messages=self.config.SQS_MAX_MESSAGES)
            
            if not messages:
                # No messages - this is normal with long polling
                return
            
            logger.info(f"📨 Processing {len(messages)} messages...")
            
            # Process each message
            for message in messages:
                try:
                    await self.process_message(message)
                    self.stats['messages_processed'] += 1
                    
                except Exception as e:
                    logger.error(f"❌ Failed to process message {message.get('message_id', 'unknown')}: {e}")
                    self.stats['processing_errors'] += 1
                    
                    # Still delete the message to prevent infinite retries
                    # In production, you might want to send to DLQ instead
                    # TODO: Rethink this because it will make debugging difficult...
                    try:
                        await self.sqs_handler.delete_message(message)
                    except Exception as delete_error:
                        logger.error(f"Failed to delete failed message: {delete_error}")
            
            self.stats['last_activity'] = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Error in processing cycle: {e}")
    
    async def process_message(self, message: Dict[str, Any]):
        """Process a single SQS message"""
        bucket = message.get('bucket')
        key = message.get('key')
        message_id = message.get('message_id')
        
        logger.info(f"🔄 Processing file: s3://{bucket}/{key}")
        
        # Create processing record in database
        record_id = await self.database_updater.create_processing_record(
            s3_bucket=bucket,
            s3_key=key
        )
        
        try:
            # Step 1: Download file from S3
            logger.info(f"⬇️  Downloading file from S3...")
            local_file_path = await self.s3_downloader.download_file(bucket, key)
            
            if not local_file_path:
                raise Exception("Failed to download file from S3")
            
            self.stats['files_downloaded'] += 1
            
            # Step 2: Get S3 metadata
            s3_metadata = await self.s3_downloader.get_file_metadata(bucket, key)
            
            # Step 3: Extract metadata and run analysis
            logger.info(f"🧠 Extracting metadata and running analysis...")
            extracted_metadata = await self.metadata_extractor.extract_metadata(
                local_file_path, 
                s3_metadata or {}
            )
            
            # Step 4: Update database with results
            if record_id:
                await self.database_updater.update_processing_status(
                    record_id,
                    status="completed",
                    metadata=extracted_metadata
                )
            
            # Step 5: Cleanup downloaded file (if configured)
            if self.config.CLEANUP_AFTER_PROCESSING:
                self.s3_downloader.cleanup_file(local_file_path)
            
            # Step 6: Delete SQS message (processing successful)
            await self.sqs_handler.delete_message(message)
            
            logger.info(f"✅ Successfully processed: s3://{bucket}/{key}")
            
        except Exception as e:
            # Update database with error
            if record_id:
                await self.database_updater.update_processing_status(
                    record_id,
                    status="failed",
                    error_message=str(e)
                )
            
            # Re-raise to handle at message level
            raise e
    
    async def print_stats(self):
        """Print service statistics"""
        uptime = datetime.utcnow() - self.stats['start_time']
        
        print("\n" + "="*50)
        print("📊 ANALYSIS SERVICE STATUS")
        print("="*50)
        print(f"⏱️  Uptime: {uptime}")
        
        # Runtime limit info
        if self.max_runtime_seconds:
            remaining_seconds = self.max_runtime_seconds - uptime.total_seconds()
            remaining_time = remaining_seconds / 3600  # Convert to hours
            if remaining_time > 0:
                print(f"⏰ Time Remaining: {remaining_time:.1f} hours")
            else:
                print(f"⏰ Time Limit: EXCEEDED")
        else:
            print(f"⏰ Time Limit: Unlimited")
            
        print(f"📨 Messages Processed: {self.stats['messages_processed']}")
        print(f"📦 Files Downloaded: {self.stats['files_downloaded']}")
        print(f"❌ Processing Errors: {self.stats['processing_errors']}")
        print(f"🕐 Last Activity: {self.stats['last_activity'] or 'None'}")
        
        # SQS queue statistics
        try:
            queue_stats = self.sqs_handler.get_queue_stats()
            print(f"📋 Queue Messages: {queue_stats.get('approximate_messages', 'Unknown')}")
            print(f"🔄 Messages in Flight: {queue_stats.get('messages_in_flight', 'Unknown')}")
        except:
            print("📋 Queue Stats: Unavailable")
        
        # Download directory statistics
        try:
            download_stats = self.s3_downloader.get_download_stats()
            print(f"📁 Download Dir Files: {download_stats.get('file_count', 'Unknown')}")
            print(f"💾 Download Dir Size: {download_stats.get('total_size_mb', 'Unknown')} MB")
        except:
            print("📁 Download Stats: Unavailable")
        
        print("="*50 + "\n")
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("🛑 Shutting down analysis service...")
        self.running = False
        
        # Print final statistics
        await self.print_stats()
        
        # Clean up resources if needed
        logger.info("✓ Analysis service stopped")

# Health check endpoint for monitoring
async def health_check():
    """Simple health check function"""
    try:
        config = Config
        config.validate()
        
        # Test SQS connection
        sqs = SQSHandler(config)
        queue_stats = sqs.get_queue_stats()
        
        # Test S3 connection
        s3 = S3Downloader(config)
        download_stats = s3.get_download_stats()
        
        return {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'queue_stats': queue_stats,
            'download_stats': download_stats
        }
        
    except Exception as e:
        return {
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }

async def main():
    """Main entry point"""
    print("🎬 DANCER Analysis Service Starting...")
    print("=" * 50)
    sys.stdout.flush()
    
    # Print environment file status early
    Config.print_env_status()
    
    # Small delay to ensure output ordering
    await asyncio.sleep(0.1)
    
    # Create service instance
    service = AnalysisService()
    
    # Start the service
    await service.start()

if __name__ == "__main__":
    # Use SelectorEventLoop on Windows for better Ctrl+C handling
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Analysis service stopped by user (Ctrl+C)")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
