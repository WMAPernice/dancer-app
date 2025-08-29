#!/usr/bin/env python3
"""
Test script for DANCER Analysis Service

This script helps test the analysis service components independently
and provides utilities for debugging and development.
"""

import asyncio
import json
import sys
import os
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from services.sqs_handler import SQSHandler
from services.s3_downloader import S3Downloader
from services.metadata_extractor import MetadataExtractor
from services.database_updater import DatabaseUpdater

async def test_configuration():
    """Test configuration loading and validation"""
    print("🔧 Testing Configuration...")
    try:
        Config.validate()
        Config.print_config()
        print("✅ Configuration valid\n")
        return True
    except Exception as e:
        print(f"❌ Configuration error: {e}\n")
        return False

async def test_sqs_connection():
    """Test SQS connection and queue access"""
    print("📡 Testing SQS Connection...")
    try:
        sqs = SQSHandler(Config)
        stats = sqs.get_queue_stats()
        print(f"✅ SQS connected successfully")
        print(f"   Queue URL: {sqs.queue_url}")
        print(f"   Messages in queue: {stats.get('approximate_messages', 'Unknown')}")
        print(f"   Messages in flight: {stats.get('messages_in_flight', 'Unknown')}\n")
        return sqs
    except Exception as e:
        print(f"❌ SQS connection failed: {e}\n")
        return None

async def test_s3_connection():
    """Test S3 connection and bucket access"""
    print("📦 Testing S3 Connection...")
    try:
        s3 = S3Downloader(Config)
        stats = s3.get_download_stats()
        print(f"✅ S3 connected successfully")
        print(f"   Bucket: {Config.S3_BUCKET}")
        print(f"   Download directory: {stats.get('download_dir', 'Unknown')}")
        print(f"   Directory exists: {stats.get('exists', False)}\n")
        return s3
    except Exception as e:
        print(f"❌ S3 connection failed: {e}\n")
        return None

async def test_database_connection():
    """Test database connection and table creation"""
    print("💾 Testing Database Connection...")
    try:
        db = DatabaseUpdater(Config)
        stats = await db.get_processing_stats()
        print(f"✅ Database connected successfully")
        print(f"   Database URL: {Config.DATABASE_URL}")
        print(f"   Total processing records: {stats.get('total_records', 0)}")
        print(f"   Completed records: {stats.get('status_counts', {}).get('completed', 0)}\n")
        return db
    except Exception as e:
        print(f"❌ Database connection failed: {e}\n")
        return None

async def test_metadata_extractor():
    """Test metadata extractor with a dummy file"""
    print("🔍 Testing Metadata Extractor...")
    try:
        extractor = MetadataExtractor(Config)
        
        # Create a dummy file for testing
        test_file = os.path.join(Config.DOWNLOAD_DIR, "test_video.mp4")
        os.makedirs(Config.DOWNLOAD_DIR, exist_ok=True)
        
        with open(test_file, 'wb') as f:
            f.write(b"dummy video content for testing")
        
        # Test metadata extraction
        dummy_s3_metadata = {
            'bucket': 'test-bucket',
            'key': 'test/video.mp4',
            'size': 25,
            'content_type': 'video/mp4'
        }
        
        metadata = await extractor.extract_metadata(test_file, dummy_s3_metadata)
        
        print(f"✅ Metadata extraction completed")
        print(f"   Extraction method: {metadata.get('video_metadata', {}).get('extraction_method', 'Unknown')}")
        print(f"   Analysis status: {metadata.get('processing_results', {}).get('status', 'Unknown')}")
        
        # Cleanup test file
        os.remove(test_file)
        print("")
        
        return extractor
    except Exception as e:
        print(f"❌ Metadata extraction failed: {e}\n")
        return None

# async def test_send_message(sqs_handler):
#     """Send a test message to SQS queue"""
#     # TODO: This only makes sense if we are sending a message to a different queue. Deactivated for now. 
#     print("📨 Testing SQS Message Sending...")
#     try:
#         test_bucket = Config.S3_BUCKET
#         test_key = f"{Config.S3_PREFIX}/test/sample_video.mp4"
        
#         success = await sqs_handler.send_test_message(test_bucket, test_key)
        
#         if success:
#             print(f"✅ Test message sent successfully")
#             print(f"   Bucket: {test_bucket}")
#             print(f"   Key: {test_key}\n")
#         else:
#             print(f"❌ Failed to send test message\n")
        
#         return success
#     except Exception as e:
#         print(f"❌ Error sending test message: {e}\n")
#         return False

async def test_poll_messages(sqs_handler):
    """Test polling messages from SQS"""
    print("📥 Testing SQS Message Polling...")
    try:
        print("   Polling for messages (5 second timeout)...")
        messages = await sqs_handler.poll_messages(max_messages=1)
        
        print(f"✅ Polling completed")
        print(f"   Messages received: {len(messages)}")
        
        if messages:
            message = messages[0]
            print(f"   Sample message bucket: {message.get('bucket', 'Unknown')}")
            print(f"   Sample message key: {message.get('key', 'Unknown')}")
            
            # Don't delete the message in test mode
            print("   (Message left in queue for actual processing)")
        
        print("")
        return messages
    except Exception as e:
        print(f"❌ Error polling messages: {e}\n")
        return []

async def run_full_test():
    """Run complete test suite"""
    print("🎬 DANCER Analysis Service Test Suite")
    print("=" * 50)
    
    # Test configuration
    if not await test_configuration():
        print("❌ Configuration test failed. Cannot continue.")
        return False
    
    # Test individual components
    sqs = await test_sqs_connection()
    s3 = await test_s3_connection()
    db = await test_database_connection()
    extractor = await test_metadata_extractor()
    
    # Component health summary
    components_healthy = all([sqs, s3, db, extractor])
    
    print("🏥 Component Health Summary:")
    print(f"   SQS Handler: {'✅ Healthy' if sqs else '❌ Failed'}")
    print(f"   S3 Downloader: {'✅ Healthy' if s3 else '❌ Failed'}")
    print(f"   Database Updater: {'✅ Healthy' if db else '❌ Failed'}")
    print(f"   Metadata Extractor: {'✅ Healthy' if extractor else '❌ Failed'}")
    print("")
    
    if not components_healthy:
        print("❌ Some components failed. Check configuration and AWS credentials.")
        return False
    
    # Test SQS operations if available
    if sqs:
        # await test_send_message(sqs)
        await test_poll_messages(sqs)
    
    print("🎉 All tests completed successfully!")
    print("   The analysis service is ready to run.")
    print("")
    
    return True

async def interactive_test():
    """Interactive test menu"""
    while True:
        print("\n🔧 DANCER Analysis Service Interactive Test")
        print("1. Test Configuration")
        print("2. Test SQS Connection")
        print("3. Test S3 Connection")
        print("4. Test Database Connection")
        print("5. Test Metadata Extractor")
        print("6. Send Test SQS Message")
        print("7. Poll SQS Messages")
        print("8. Run Full Test Suite")
        print("9. Exit")
        
        choice = input("\nSelect option (1-9): ").strip()
        
        if choice == "1":
            await test_configuration()
        elif choice == "2":
            await test_sqs_connection()
        elif choice == "3":
            await test_s3_connection()
        elif choice == "4":
            await test_database_connection()
        elif choice == "5":
            await test_metadata_extractor()
        elif choice == "6":
            sqs = await test_sqs_connection()
            print("🚧 This test is deactivated for now.")
            # if sqs:
            #     await test_send_message(sqs)
        elif choice == "7":
            sqs = await test_sqs_connection()
            if sqs:
                await test_poll_messages(sqs)
        elif choice == "8":
            await run_full_test()
        elif choice == "9":
            print("👋 Exiting test suite")
            break
        else:
            print("❌ Invalid option. Please select 1-9.")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test DANCER Analysis Service")
    parser.add_argument("--interactive", "-i", action="store_true", help="Run interactive test menu")
    parser.add_argument("--full", "-f", action="store_true", help="Run full test suite")
    
    args = parser.parse_args()
    
    try:
        if args.interactive:
            asyncio.run(interactive_test())
        elif args.full:
            asyncio.run(run_full_test())
        else:
            # Default: run full test
            asyncio.run(run_full_test())
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
