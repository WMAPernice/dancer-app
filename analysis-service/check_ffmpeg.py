#!/usr/bin/env python3
"""
Check if FFmpeg/ffprobe is installed and accessible
"""

import subprocess
import sys

def check_ffmpeg():
    """Check if ffprobe is available"""
    try:
        result = subprocess.run(
            ['ffprobe', '-version'], 
            capture_output=True, 
            text=True, 
            timeout=5,
            stdin=subprocess.DEVNULL
        )
        
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✅ FFmpeg found: {version_line}")
            return True
        else:
            print(f"❌ FFprobe returned error: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("❌ FFprobe not found in PATH")
        print_installation_instructions()
        return False
    except subprocess.TimeoutExpired:
        print("❌ FFprobe command timed out")
        return False
    except Exception as e:
        print(f"❌ Error checking FFprobe: {e}")
        return False

def print_installation_instructions():
    """Print platform-specific installation instructions"""
    print("\n📋 Installation Instructions:")
    print("-" * 30)
    
    if sys.platform == "win32":
        print("Windows:")
        print("  1. Using Chocolatey: choco install ffmpeg")
        print("  2. Using Scoop: scoop install ffmpeg")
        print("  3. Manual: Download from https://ffmpeg.org/download.html")
        print("     - Extract to C:\\ffmpeg")
        print("     - Add C:\\ffmpeg\\bin to your PATH")
        
    elif sys.platform == "darwin":
        print("macOS:")
        print("  1. Using Homebrew: brew install ffmpeg")
        print("  2. Using MacPorts: sudo port install ffmpeg")
        
    else:
        print("Linux:")
        print("  Ubuntu/Debian: sudo apt install ffmpeg")
        print("  CentOS/RHEL: sudo yum install ffmpeg")
        print("  Arch: sudo pacman -S ffmpeg")

if __name__ == "__main__":
    print("🔍 Checking FFmpeg installation...")
    if check_ffmpeg():
        print("🎉 FFmpeg is ready for video metadata extraction!")
    else:
        print("💡 Install FFmpeg to enable video metadata extraction.")
        print("   The analysis service will work without it but with limited metadata.")
