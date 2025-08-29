"""
Metadata Extraction Service - Placeholder for downstream processing scripts
"""

import os
import json
import logging
from typing import Dict, Any, Optional
import subprocess
from datetime import datetime

logger = logging.getLogger(__name__)

class MetadataExtractor:
    """Handles video metadata extraction and processing"""
    
    def __init__(self, config):
        self.config = config
    
    @staticmethod
    def get_real_metadata_only(full_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract only the real metadata (no placeholder analysis)
        
        Args:
            full_metadata: Complete metadata dictionary from extract_metadata()
            
        Returns:
            Dictionary containing only real metadata (file, S3, video technical data)
        """
        return {
            'processing_info': full_metadata.get('processing_info', {}),
            'real_metadata': full_metadata.get('real_metadata', {})
        }
    
    @staticmethod
    def get_placeholder_analysis_only(full_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract only the placeholder analysis results
        
        Args:
            full_metadata: Complete metadata dictionary from extract_metadata()
            
        Returns:
            Dictionary containing only placeholder analysis data
        """
        return {
            'processing_info': full_metadata.get('processing_info', {}),
            'placeholder_analysis': full_metadata.get('placeholder_analysis', {})
        }
    
    async def extract_metadata(self, file_path: str, s3_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata from downloaded video file
        
        Args:
            file_path: Local path to video file
            s3_metadata: Metadata from S3 object
            
        Returns:
            Dictionary containing extracted metadata
        """
        logger.info(f"🔍 Extracting metadata from: {file_path}")
        
        # Structure metadata to clearly separate real data from placeholder analysis
        metadata = {
            'processing_info': {
                'processing_timestamp': datetime.utcnow().isoformat(),
                'processor_version': '1.0.0',
                'extraction_status': 'completed'
            },
            
            # REAL METADATA - Extracted from actual file and S3
            'real_metadata': {
                'file_info': self._get_file_info(file_path),
                's3_info': s3_metadata,
                'video_technical_metadata': await self._extract_video_metadata(file_path)
            },
            
            # PLACEHOLDER ANALYSIS - Simulated results (TO BE REPLACED)
            'placeholder_analysis': {
                'note': 'THIS IS PLACEHOLDER DATA - Replace with actual gait analysis',
                'analysis_results': await self._run_placeholder_analysis(file_path),
                'warning': 'These results are simulated for demonstration purposes only'
            }
        }
        
        # Print extracted metadata with clear distinction
        self._print_metadata_summary(metadata)
        
        return metadata
    
    def _get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get basic file information"""
        try:
            stat = os.stat(file_path)
            return {
                'local_path': file_path,
                'filename': os.path.basename(file_path),
                'file_size_bytes': stat.st_size,
                'file_size_mb': round(stat.st_size / (1024 * 1024), 2),
                'file_extension': os.path.splitext(file_path)[1].lower(),
                'modification_time': datetime.fromtimestamp(stat.st_mtime).isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get file info: {e}")
            return {'error': str(e)}
    
    async def _extract_video_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract video metadata using ffprobe (if available)
        Falls back to basic file analysis if ffprobe not available
        """
        try:
            # Try using ffprobe for detailed video metadata
            return await self._extract_with_ffprobe(file_path)
        except Exception as e:
            logger.warning(f"ffprobe extraction failed: {e}")
            # Fallback to basic analysis
            return await self._extract_basic_video_info(file_path)
    
    async def _extract_with_ffprobe(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata using ffprobe"""
        try:
            # Check if ffprobe is available
            try:
                subprocess.run(['ffprobe', '-version'], 
                             capture_output=True, 
                             text=True, 
                             timeout=5,
                             check=True)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                raise Exception("ffprobe not found - install ffmpeg to enable video metadata extraction")
            
            # Run ffprobe command
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout
                stdin=subprocess.DEVNULL  # Prevent hanging on input
            )
            
            if result.returncode == 0:
                probe_data = json.loads(result.stdout)
                
                # Extract video stream information
                video_streams = [s for s in probe_data.get('streams', []) if s.get('codec_type') == 'video']
                audio_streams = [s for s in probe_data.get('streams', []) if s.get('codec_type') == 'audio']
                
                metadata = {
                    'extraction_method': 'ffprobe',
                    'format': probe_data.get('format', {}),
                    'video_streams': len(video_streams),
                    'audio_streams': len(audio_streams),
                    'duration_seconds': float(probe_data.get('format', {}).get('duration', 0)),
                    'bitrate': int(probe_data.get('format', {}).get('bit_rate', 0)),
                    'file_size': int(probe_data.get('format', {}).get('size', 0))
                }
                
                # Add primary video stream details if available
                if video_streams:
                    primary_video = video_streams[0]
                    metadata['video_details'] = {
                        'codec': primary_video.get('codec_name'),
                        'width': primary_video.get('width'),
                        'height': primary_video.get('height'),
                        'fps': self._parse_fps(primary_video.get('r_frame_rate')),
                        'aspect_ratio': primary_video.get('display_aspect_ratio'),
                        'pixel_format': primary_video.get('pix_fmt')
                    }
                
                return metadata
            else:
                raise Exception(f"ffprobe failed with return code {result.returncode}: {result.stderr}")
                
        except FileNotFoundError:
            raise Exception("ffprobe not found - install ffmpeg to enable video metadata extraction")
        except subprocess.TimeoutExpired:
            raise Exception("ffprobe timed out")
        except json.JSONDecodeError:
            raise Exception("Failed to parse ffprobe output")
        except Exception as e:
            raise Exception(f"ffprobe extraction failed: {e}")
    
    async def _extract_basic_video_info(self, file_path: str) -> Dict[str, Any]:
        """Basic video file analysis without external tools"""
        try:
            file_extension = os.path.splitext(file_path)[1].lower()
            
            # Basic video format detection based on extension
            format_info = {
                '.mp4': {'format': 'MP4', 'likely_codec': 'H.264'},
                '.avi': {'format': 'AVI', 'likely_codec': 'Various'},
                '.mov': {'format': 'QuickTime', 'likely_codec': 'H.264'},
                '.mkv': {'format': 'Matroska', 'likely_codec': 'Various'},
                '.wmv': {'format': 'Windows Media', 'likely_codec': 'WMV'},
                '.flv': {'format': 'Flash Video', 'likely_codec': 'H.264'}
            }.get(file_extension, {'format': 'Unknown', 'likely_codec': 'Unknown'})
            
            return {
                'extraction_method': 'basic_analysis',
                'file_extension': file_extension,
                'detected_format': format_info['format'],
                'likely_codec': format_info['likely_codec'],
                'note': 'Limited metadata - install ffmpeg for detailed analysis'
            }
            
        except Exception as e:
            logger.error(f"Basic video analysis failed: {e}")
            return {
                'extraction_method': 'failed',
                'error': str(e)
            }
    
    def _parse_fps(self, fps_string: str) -> Optional[float]:
        """Parse fps from ffprobe fraction format (e.g., '30/1')"""
        try:
            if '/' in fps_string:
                num, den = fps_string.split('/')
                return round(float(num) / float(den), 2)
            else:
                return float(fps_string)
        except:
            return None
    
    async def _run_placeholder_analysis(self, file_path: str) -> Dict[str, Any]:
        """
        Placeholder for downstream analysis scripts
        This is where you would call your actual analysis algorithms
        """
        logger.info("🚀 Running placeholder analysis script...")
        
        # Simulate processing time
        import asyncio
        await asyncio.sleep(1)
        
        # Placeholder analysis results
        analysis_results = {
            'analysis_type': 'placeholder_gait_analysis',
            'status': 'completed',
            'processing_time_seconds': 1.0,
            'placeholder_results': {
                'gait_cycle_detected': True,
                'estimated_stride_length': 1.25,  # meters
                'estimated_cadence': 110,  # steps per minute
                'estimated_walking_speed': 1.4,  # m/s
                'confidence_score': 0.85,
                'notes': [
                    'This is a placeholder analysis',
                    'Replace with actual gait analysis algorithm',
                    'Results are simulated for demonstration'
                ]
            },
            'next_steps': [
                'Implement actual video processing pipeline',
                'Add machine learning models for gait analysis',
                'Integrate with clinical assessment tools'
            ]
        }
        
        logger.info("✓ Placeholder analysis completed")
        return analysis_results
    
    def _print_metadata_summary(self, metadata: Dict[str, Any]):
        """Print a summary of extracted metadata with clear distinction between real and placeholder data"""
        print("\n" + "="*70)
        print("📊 METADATA EXTRACTION SUMMARY")
        print("="*70)
        
        # Processing information
        processing_info = metadata.get('processing_info', {})
        print(f"🕒 Processed: {processing_info.get('processing_timestamp', 'Unknown')}")
        print(f"📦 Processor Version: {processing_info.get('processor_version', 'Unknown')}")
        
        print("\n" + "📋 REAL METADATA (Extracted from actual file/S3)")
        print("-" * 50)
        
        real_metadata = metadata.get('real_metadata', {})
        
        # File information
        file_info = real_metadata.get('file_info', {})
        print(f"📁 File: {file_info.get('filename', 'Unknown')}")
        print(f"📏 Size: {file_info.get('file_size_mb', 0)} MB")
        print(f"📅 Modified: {file_info.get('modification_time', 'Unknown')}")
        print(f"🔧 Extension: {file_info.get('file_extension', 'Unknown')}")
        
        # S3 information
        s3_info = real_metadata.get('s3_info', {})
        print(f"☁️  S3 Location: s3://{s3_info.get('bucket', 'unknown')}/{s3_info.get('key', 'unknown')}")
        print(f"📝 Content Type: {s3_info.get('content_type', 'Unknown')}")
        print(f"🏷️  ETag: {s3_info.get('etag', 'Unknown')}")
        print(f"📦 Storage Class: {s3_info.get('storage_class', 'Unknown')}")
        
        # Video technical metadata
        video_meta = real_metadata.get('video_technical_metadata', {})
        print(f"🎬 Extraction Method: {video_meta.get('extraction_method', 'Unknown')}")
        
        if 'video_details' in video_meta:
            details = video_meta['video_details']
            print(f"📺 Resolution: {details.get('width', '?')}x{details.get('height', '?')}")
            print(f"🎞️  FPS: {details.get('fps', '?')}")
            print(f"🔧 Codec: {details.get('codec', 'Unknown')}")
            print(f"📐 Aspect Ratio: {details.get('aspect_ratio', 'Unknown')}")
            print(f"🎨 Pixel Format: {details.get('pixel_format', 'Unknown')}")
        
        if 'duration_seconds' in video_meta:
            duration = video_meta['duration_seconds']
            print(f"⏱️  Duration: {duration} seconds ({duration/60:.1f} minutes)")
        
        if 'bitrate' in video_meta:
            bitrate = video_meta['bitrate']
            print(f"📊 Bitrate: {bitrate} bps ({bitrate/1000000:.1f} Mbps)")
        
        if 'video_streams' in video_meta:
            print(f"🎥 Video Streams: {video_meta['video_streams']}")
        
        if 'audio_streams' in video_meta:
            print(f"🔊 Audio Streams: {video_meta['audio_streams']}")
        
        # Placeholder analysis section
        print("\n" + "🚧 PLACEHOLDER ANALYSIS (SIMULATED DATA - TO BE REPLACED)")
        print("-" * 50)
        
        placeholder_analysis = metadata.get('placeholder_analysis', {})
        analysis_results = placeholder_analysis.get('analysis_results', {})
        
        print(f"⚠️  WARNING: {placeholder_analysis.get('warning', 'Unknown')}")
        print(f"🧠 Analysis Status: {analysis_results.get('status', 'Unknown')}")
        
        if 'placeholder_results' in analysis_results:
            results = analysis_results['placeholder_results']
            print(f"🚶 Gait Detected: {results.get('gait_cycle_detected', False)} (SIMULATED)")
            print(f"📏 Stride Length: {results.get('estimated_stride_length', 0)} m (SIMULATED)")
            print(f"🥾 Cadence: {results.get('estimated_cadence', 0)} steps/min (SIMULATED)")
            print(f"🏃 Walking Speed: {results.get('estimated_walking_speed', 0)} m/s (SIMULATED)")
            print(f"🎯 Confidence: {results.get('confidence_score', 0)*100:.1f}% (SIMULATED)")
        
        print("\n" + "💡 NEXT STEPS:")
        next_steps = analysis_results.get('next_steps', [])
        for i, step in enumerate(next_steps, 1):
            print(f"   {i}. {step}")
        
        print("\n" + "="*70)
        print("✅ REAL metadata extraction completed successfully!")
        print("🔄 Replace placeholder analysis with actual gait analysis algorithms.")
        print("="*70 + "\n")
