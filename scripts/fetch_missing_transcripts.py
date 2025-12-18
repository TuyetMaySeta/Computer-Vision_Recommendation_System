#!/usr/bin/env python3
"""
Script để lấy transcripts cho các video trong database (VERSION 2 - FIXED)
FIXED: Không ghi đè transcript đã lấy được, ưu tiên method tốt nhất
"""

import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.models import execute_query
from database.connection import DatabaseConnection
from utils.logger import get_logger

logger = get_logger(__name__)

# Import các thư viện transcript
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import (
        TranscriptsDisabled, 
        NoTranscriptFound,
        VideoUnavailable
    )
    HAS_TRANSCRIPT_API = True
except ImportError:
    HAS_TRANSCRIPT_API = False
    logger.warning("youtube-transcript-api not installed")

try:
    import yt_dlp
    HAS_YT_DLP = True
except ImportError:
    HAS_YT_DLP = False
    logger.warning("yt-dlp not installed")


class TranscriptFetcherV2:
    def __init__(self):
        self.success_count = 0
        self.fail_count = 0
        self.method1_success = 0
        self.method2_success = 0
        
    def get_transcript_method1(self, video_id):
        """
        Method 1: youtube-transcript-api (FASTEST & BEST)
        Trả về (transcript_text, method_name) hoặc (None, None)
        """
        if not HAS_TRANSCRIPT_API:
            return None, None
            
        try:
            # Lấy danh sách transcripts
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            method_name = None
            
            # Priority 1: Manual transcript (BEST QUALITY)
            try:
                transcript = transcript_list.find_manually_created_transcript(['en', 'en-US', 'en-GB'])
                method_name = "manual"
            except NoTranscriptFound:
                # Priority 2: Auto-generated
                try:
                    transcript = transcript_list.find_generated_transcript(['en', 'en-US', 'en-GB'])
                    method_name = "auto-generated"
                except NoTranscriptFound:
                    # Priority 3: Translate to English
                    try:
                        for lang in ['vi', 'es', 'fr', 'de', 'ja', 'ko', 'zh', 'hi', 'ar']:
                            try:
                                transcript = transcript_list.find_transcript([lang])
                                transcript = transcript.translate('en')
                                method_name = f"translated-{lang}"
                                break
                            except:
                                continue
                        if method_name is None:
                            return None, None
                    except:
                        return None, None
            
            # Fetch transcript data
            transcript_data = transcript.fetch()
            
            # Combine segments
            full_text = ' '.join([entry['text'] for entry in transcript_data])
            
            # Clean
            full_text = full_text.replace('\n', ' ')
            full_text = ' '.join(full_text.split())  # Normalize whitespace
            
            if not full_text or len(full_text) < 50:
                return None, None
            
            return full_text.strip(), method_name
            
        except TranscriptsDisabled:
            return None, None
        except VideoUnavailable:
            return None, None
        except Exception as e:
            logger.debug(f"Method1 error for {video_id}: {str(e)}")
            return None, None
    
    def get_transcript_method2(self, video_id):
        """
        Method 2: yt-dlp (FALLBACK)
        Chỉ dùng khi method 1 thất bại
        """
        if not HAS_YT_DLP:
            return None, None
            
        try:
            ydl_opts = {
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['en'],
                'quiet': True,
                'no_warnings': True,
            }
            
            url = f'https://www.youtube.com/watch?v={video_id}'
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Try manual subtitles first
                if 'subtitles' in info and 'en' in info['subtitles']:
                    subtitle_data = info['subtitles']['en']
                    if subtitle_data:
                        subtitle_url = subtitle_data[0]['url']
                        import requests
                        response = requests.get(subtitle_url, timeout=10)
                        text = self._parse_subtitle_text(response.text)
                        
                        if text and len(text) >= 50:
                            return text, "yt-dlp-manual"
                
                # Try auto-captions
                if 'automatic_captions' in info and 'en' in info['automatic_captions']:
                    caption_data = info['automatic_captions']['en']
                    if caption_data:
                        caption_url = caption_data[0]['url']
                        import requests
                        response = requests.get(caption_url, timeout=10)
                        text = self._parse_subtitle_text(response.text)
                        
                        if text and len(text) >= 50:
                            return text, "yt-dlp-auto"
                
                return None, None
                
        except Exception as e:
            logger.debug(f"Method2 error for {video_id}: {str(e)}")
            return None, None
    
    def _parse_subtitle_text(self, subtitle_content):
        """Parse VTT or SRT subtitle format"""
        lines = subtitle_content.split('\n')
        text_lines = []
        
        for line in lines:
            line = line.strip()
            # Skip timestamps, metadata, and empty lines
            if (line and 
                not line.startswith('WEBVTT') and 
                not line.startswith('NOTE') and
                '-->' not in line and 
                not line.isdigit() and
                not line.startswith('<') and
                len(line) > 2):
                text_lines.append(line)
        
        text = ' '.join(text_lines)
        text = ' '.join(text.split())  # Normalize whitespace
        return text
    
    def get_transcript(self, video_id):
        """
        Try multiple methods in priority order
        FIXED: Dừng ngay khi tìm được transcript tốt
        """
        # Method 1: youtube-transcript-api (PRIORITY)
        transcript, method = self.get_transcript_method1(video_id)
        
        if transcript and len(transcript) >= 50:
            self.success_count += 1
            self.method1_success += 1
            logger.info(f"  ✓ Method 1 SUCCESS ({method}): {len(transcript)} chars")
            return transcript, f"method1-{method}"
        
        # Method 2: yt-dlp (FALLBACK only if method 1 failed)
        logger.debug(f"  → Trying method 2 (fallback)...")
        transcript, method = self.get_transcript_method2(video_id)
        
        if transcript and len(transcript) >= 50:
            self.success_count += 1
            self.method2_success += 1
            logger.info(f"  ✓ Method 2 SUCCESS ({method}): {len(transcript)} chars")
            return transcript, f"method2-{method}"
        
        # Failed both methods
        self.fail_count += 1
        return None, None
    
    def update_video_transcript(self, video_id, transcript_text):
        """Update transcript in database"""
        query = """
        UPDATE videos 
        SET transcript_text = %s, 
            updated_at = CURRENT_TIMESTAMP
        WHERE video_id = %s
        """
        
        try:
            execute_query(query, (transcript_text, video_id))
            return True
        except Exception as e:
            logger.error(f"DB update error for {video_id}: {e}")
            return False


def fetch_missing_transcripts(batch_size=10, delay=1.0, limit=None, min_chars=100):
    """
    Main function - FIXED VERSION
    
    Args:
        batch_size: Videos per batch
        delay: Delay between batches (seconds)
        limit: Max videos to process
        min_chars: Minimum transcript length
    """
    logger.info("=" * 80)
    logger.info("FETCHING MISSING TRANSCRIPTS (VERSION 2 - FIXED)")
    logger.info("=" * 80)
    
    # Check libraries
    logger.info("\nAvailable methods:")
    logger.info(f"  - youtube-transcript-api: {'✓ YES' if HAS_TRANSCRIPT_API else '✗ NO'}")
    logger.info(f"  - yt-dlp: {'✓ YES' if HAS_YT_DLP else '✗ NO'}")
    
    if not HAS_TRANSCRIPT_API and not HAS_YT_DLP:
        logger.error("\n❌ No transcript libraries!")
        logger.error("Install: pip install youtube-transcript-api yt-dlp")
        return False
    
    # Get videos without transcripts
    logger.info("\n[Step 1/3] Loading videos from database...")
    
    query = """
    SELECT video_id, title, channel_name, view_count
    FROM videos
    WHERE transcript_text IS NULL OR transcript_text = '' OR LENGTH(transcript_text) < %s
    ORDER BY view_count DESC
    """
    
    if limit:
        query += f" LIMIT {limit}"
    
    videos = execute_query(query, (min_chars,), fetch=True)
    
    if not videos:
        logger.info("✅ All videos have good transcripts!")
        return True
    
    logger.info(f"Found {len(videos)} videos needing transcripts")
    
    # Process
    fetcher = TranscriptFetcherV2()
    start_time = time.time()
    
    logger.info("\n[Step 2/3] Fetching transcripts...")
    logger.info(f"Config: batch_size={batch_size}, delay={delay}s, min_chars={min_chars}")
    logger.info("-" * 80)
    
    for i, video in enumerate(videos):
        video_id = video['video_id']
        title = video['title'][:70]
        
        # Progress
        progress = f"[{i+1}/{len(videos)}]"
        logger.info(f"\n{progress} {title}")
        logger.info(f"  Video ID: {video_id}")
        logger.info(f"  Channel: {video['channel_name']}")
        
        # Get transcript
        transcript, method = fetcher.get_transcript(video_id)
        
        if transcript:
            # Validate length
            if len(transcript) < min_chars:
                logger.warning(f"  ⚠ Too short: {len(transcript)} chars (min: {min_chars})")
                fetcher.fail_count += 1
                fetcher.success_count -= 1
                continue
            
            # Update database
            if fetcher.update_video_transcript(video_id, transcript):
                logger.info(f"  ✅ SAVED to database")
            else:
                logger.error(f"  ❌ Failed to save")
        else:
            logger.warning(f"  ⚠ SKIPPED: No transcript available")
        
        # Batch delay
        if (i + 1) % batch_size == 0 and (i + 1) < len(videos):
            logger.info(f"\n{'='*80}")
            logger.info(f"Batch {(i+1)//batch_size} complete. Pausing {delay}s...")
            logger.info(f"Progress: {i+1}/{len(videos)} ({(i+1)/len(videos)*100:.1f}%)")
            logger.info(f"Success rate: {fetcher.success_count}/{i+1} ({fetcher.success_count/(i+1)*100:.1f}%)")
            logger.info(f"{'='*80}\n")
            time.sleep(delay)
    
    # Summary
    elapsed = time.time() - start_time
    
    logger.info("\n" + "=" * 80)
    logger.info("[Step 3/3] SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total processed: {len(videos)}")
    logger.info(f"Successful: {fetcher.success_count} ({fetcher.success_count/len(videos)*100:.1f}%)")
    logger.info(f"Failed: {fetcher.fail_count} ({fetcher.fail_count/len(videos)*100:.1f}%)")
    logger.info(f"\nMethod breakdown:")
    logger.info(f"  Method 1 (youtube-transcript-api): {fetcher.method1_success}")
    logger.info(f"  Method 2 (yt-dlp fallback): {fetcher.method2_success}")
    logger.info(f"\nTime: {elapsed/60:.1f} minutes")
    logger.info(f"Avg: {elapsed/len(videos):.1f}s per video")
    
    # Database stats
    query_stats = """
    SELECT 
        COUNT(*) as total,
        COUNT(CASE WHEN transcript_text IS NOT NULL AND transcript_text != '' THEN 1 END) as with_transcript,
        AVG(LENGTH(transcript_text)) as avg_length
    FROM videos
    WHERE transcript_text IS NOT NULL AND transcript_text != ''
    """
    
    stats = execute_query(query_stats, fetch=True)[0]
    
    logger.info(f"\nDatabase stats:")
    logger.info(f"  Total videos: {stats['total']}")
    logger.info(f"  With transcript: {stats['with_transcript']}")
    logger.info(f"  Avg length: {stats['avg_length']:.0f} chars")
    logger.info("=" * 80)
    
    return True


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Fetch missing transcripts (FIXED VERSION)'
    )
    
    parser.add_argument('-b', '--batch-size', type=int, default=10)
    parser.add_argument('-d', '--delay', type=float, default=1.0)
    parser.add_argument('-l', '--limit', type=int, default=None)
    parser.add_argument('-m', '--min-chars', type=int, default=100,
                       help='Minimum transcript length (default: 100)')
    
    args = parser.parse_args()
    
    try:
        DatabaseConnection.initialize_pool()
        
        success = fetch_missing_transcripts(
            batch_size=args.batch_size,
            delay=args.delay,
            limit=args.limit,
            min_chars=args.min_chars
        )
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("\n\nInterrupted by user")
        return 1
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}", exc_info=True)
        return 1
    finally:
        DatabaseConnection.close_all_connections()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)