#!/usr/bin/env python3
"""
Test script to verify Ctrl+C handling works properly
"""

import asyncio
import signal
import sys

async def test_interrupt_handling():
    """Test that Ctrl+C interrupts work in asyncio loops"""
    
    print("🧪 Testing interrupt handling...")
    print("Press Ctrl+C to test interrupt handling")
    print("The script should exit cleanly within 2 seconds")
    print("-" * 50)
    
    try:
        counter = 0
        while True:
            counter += 1
            print(f"⏱️  Running... {counter} seconds (Press Ctrl+C to stop)")
            await asyncio.sleep(1)
            
            # Auto-exit after 30 seconds if no interrupt
            if counter >= 30:
                print("⏰ Auto-exit after 30 seconds")
                break
                
    except KeyboardInterrupt:
        print("\n✅ Keyboard interrupt caught successfully!")
        print("🎉 Ctrl+C handling is working properly")
        return True
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False
    
    print("\n⚠️  No interrupt received (test completed)")
    return True

async def main():
    await test_interrupt_handling()

if __name__ == "__main__":
    # Use same event loop policy as main script
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✅ Top-level KeyboardInterrupt caught!")
        print("🎉 Interrupt handling is working at all levels")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
    
    print("👋 Test completed")
