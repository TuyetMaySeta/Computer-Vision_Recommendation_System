#!/usr/bin/env python3
"""
Advanced transcript fetcher - Multiple methods with fallbacks
Sử dụng YouTube Internal API trực tiếp
"""

import sys
import os
import time
import json
import requests
import re
from urllib.parse import quote

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.models import execute_query
from database.connection import DatabaseConnection
from utils.logger import get_logger

logger = get_logger(__name__)


class AdvancedTranscriptFetcher:
    def __init__(self):
        self.success_count = 0
        self.fail_count = 0
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
        
    def method1_youtube_internal_api(self, video_id):
        """
        Method 1: YouTube Internal API (Không cần API key)
        Crawl trực tiếp từ YouTube như trình duyệt
        """
        try:
            # Step 1: Lấy webpage để extract API key và context
            url = f'https://www.youtube.com/watch?v={video_id}'
            response = self.session.get(url, timeout=10)
            
            if response.status_code != 200:
                return None
            
            html = response.text
            
            # Extract ytInitialPlayerResponse (chứa caption tracks)
            match = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?});', html)
            if not match:
                return None
            
            player_response = json.loads(match.group(1))
            
            # Extract captions
            captions = player_response.get('captions', {})
            caption_tracks = captions.get('playerCaptionsTracklistRenderer', {}).get('captionTracks', [])
            
            if not caption_tracks:
                return None
            
            # Tìm English caption (ưu tiên manual)
            caption_url = None
            for track in caption_tracks:
                if track.get('languageCode', '').startswith('en'):
                    caption_url = track.get('baseUrl')
                    if track.get('kind') != 'asr':  # Manual transcript
                        break
            
            if not caption_url:
                return None
            
            # Step 2: Lấy transcript từ caption URL
            caption_response = self.session.get(caption_url, timeout=10)
            
            if caption_response.status_code != 200:
                return None
            
            # Parse XML transcript
            transcript_text = self._parse_xml_transcript(caption_response.text)
            
            if transcript_text and len(transcript_text) >= 100:
                logger.info(f"  ✓ Method 1 (Internal API): {len(transcript_text)} chars")
                return transcript_text
            
            return None
            
        except Exception as e:
            logger.debug(f"  Method 1 error: {str(e)}")
            return None
    
    def method2_timedtext_api(self, video_id):
        """
        Method 2: YouTube TimedText API (Direct)
        """
        try:
            # Get caption track list
            url = f'https://www.youtube.com/api/timedtext?v={video_id}&type=list'
            response = self.session.get(url, timeout=10)
            
            if response.status_code != 200:
                return None
            
            # Parse available languages
            tracks = re.findall(r'lang_code="([^"]+)".*?name="([^"]*)"', response.text)
            
            # Try to find English
            lang_code = None
            for code, name in tracks:
                if code.startswith('en') or 'English' in name:
                    lang_code = code
                    if 'auto' not in name.lower():  # Prefer manual
                        break
            
            if not lang_code:
                return None
            
            # Get transcript
            transcript_url = f'https://www.youtube.com/api/timedtext?v={video_id}&lang={lang_code}'
            transcript_response = self.session.get(transcript_url, timeout=10)
            
            if transcript_response.status_code != 200:
                return None
            
            transcript_text = self._parse_xml_transcript(transcript_response.text)
            
            if transcript_text and len(transcript_text) >= 100:
                logger.info(f"  ✓ Method 2 (TimedText API): {len(transcript_text)} chars")
                return transcript_text
            
            return None
            
        except Exception as e:
            logger.debug(f"  Method 2 error: {str(e)}")
            return None
    
    def method3_youtube_transcript_api(self, video_id):
        """
        Method 3: youtube-transcript-api library (fallback)
        """
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            from youtube_transcript_api._errors import NoTranscriptFound
            
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Try manual first
            try:
                transcript = transcript_list.find_manually_created_transcript(['en'])
            except:
                transcript = transcript_list.find_generated_transcript(['en'])
            
            transcript_data = transcript.fetch()
            text = ' '.join([entry['text'] for entry in transcript_data])
            
            if text and len(text) >= 100:
                logger.info(f"  ✓ Method 3 (Library): {len(text)} chars")
                return text
            
            return None
            
        except Exception as e:
            logger.debug(f"  Method 3 error: {str(e)}")
            return None
    
    def method4_selenium_crawler(self, video_id):
        """
        Method 4: Selenium - Chạy browser thật (HEAVY but WORKS)
        """
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.chrome.options import Options
            
            # Setup headless Chrome
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            
            driver = webdriver.Chrome(options=chrome_options)
            
            try:
                url = f'https://www.youtube.com/watch?v={video_id}'
                driver.get(url)
                
                # Wait for page load
                time.sleep(3)
                
                # Click "Show transcript" button
                try:
                    # Find and click transcript button
                    transcript_button = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, '//button[@aria-label="Show transcript"]'))
                    )
                    transcript_button.click()
                    time.sleep(2)
                    
                    # Get transcript segments
                    segments = driver.find_elements(By.CSS_SELECTOR, 'yt-formatted-string.segment-text')
                    
                    text = ' '.join([seg.text for seg in segments if seg.text])
                    
                    if text and len(text) >= 100:
                        logger.info(f"  ✓ Method 4 (Selenium): {len(text)} chars")
                        return text
                    
                except:
                    pass
                
                return None
                
            finally:
                driver.quit()
                
        except Exception as e:
            logger.debug(f"  Method 4 error: {str(e)}")
            return None
    
    def method5_extract_from_json(self, video_id):
        """
        Method 5: Extract từ JSON embedded trong page
        """
        try:
            url = f'https://www.youtube.com/watch?v={video_id}'
            response = self.session.get(url, timeout=10)
            
            if response.status_code != 200:
                return None
            
            html = response.text
            
            # Tìm tất cả các JSON objects trong page
            json_objects = re.findall(r'var ytInitialData = ({.+?});', html)
            
            for json_str in json_objects:
                try:
                    data = json.loads(json_str)
                    
                    # Recursive search for transcript data
                    transcript = self._find_transcript_in_json(data)
                    
                    if transcript and len(transcript) >= 100:
                        logger.info(f"  ✓ Method 5 (JSON Extract): {len(transcript)} chars")
                        return transcript
                        
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.debug(f"  Method 5 error: {str(e)}")
            return None
    
    def _parse_xml_transcript(self, xml_text):
        """Parse XML transcript format"""
        import xml.etree.ElementTree as ET
        
        try:
            root = ET.fromstring(xml_text)
            
            segments = []
            for text_elem in root.findall('.//text'):
                text = text_elem.text
                if text:
                    # Clean text
                    text = re.sub(r'<[^>]+>', '', text)  # Remove HTML tags
                    text = text.replace('\n', ' ')
                    segments.append(text.strip())
            
            return ' '.join(segments)
            
        except Exception as e:
            logger.debug(f"XML parse error: {e}")
            return None
    
    def _find_transcript_in_json(self, obj, depth=0, max_depth=10):
        """Recursively search for transcript in JSON"""
        if depth > max_depth:
            return None
        
        if isinstance(obj, dict):
            # Look for transcript-like keys
            for key in ['transcript', 'captions', 'subtitles', 'text', 'content']:
                if key in obj and isinstance(obj[key], str) and len(obj[key]) > 100:
                    return obj[key]
            
            # Recurse
            for value in obj.values():
                result = self._find_transcript_in_json(value, depth + 1, max_depth)
                if result:
                    return result
        
        elif isinstance(obj, list):
            for item in obj:
                result = self._find_transcript_in_json(item, depth + 1, max_depth)
                if result:
                    return result
        
        return None
    
    def get_transcript(self, video_id, max_retries=3):
        """
        Try all methods with retries
        """
        methods = [
            ('Internal API', self.method1_youtube_internal_api),
            ('TimedText API', self.method2_timedtext_api),
            ('Library', self.method3_youtube_transcript_api),
            ('JSON Extract', self.method5_extract_from_json),
            # ('Selenium', self.method4_selenium_crawler),  # Uncomment nếu cần
        ]
        
        for method_name, method_func in methods:
            for attempt in range(max_retries):
                try:
                    transcript = method_func(video_id)
                    
                    if transcript:
                        self.success_count += 1
                        return transcript, method_name
                    
                except Exception as e:
                    logger.debug(f"  Attempt {attempt+1}/{max_retries} for {method_name}: {e}")
                    time.sleep(1)
        
        # All methods failed
        self.fail_count += 1
        return None, None
    
    def update_video_transcript(self, video_id, transcript_text):
        """Update database"""
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
            logger.error(f"DB update error: {e}")
            return False


def fetch_transcripts_advanced(batch_size=10, delay=2.0, limit=None):
    """
    Main function với multiple methods
    """
    logger.info("=" * 80)
    logger.info("ADVANCED TRANSCRIPT FETCHER - MULTIPLE METHODS")
    logger.info("=" * 80)
    
    # Get videos
    query = """
    SELECT video_id, title, channel_name, view_count
    FROM videos
    WHERE transcript_text IS NULL OR transcript_text = ''
    ORDER BY view_count DESC
    """
    
    if limit:
        query += f" LIMIT {limit}"
    
    videos = execute_query(query, fetch=True)
    
    if not videos:
        logger.info("✅ All videos have transcripts!")
        return True
    
    logger.info(f"\nFound {len(videos)} videos without transcripts")
    
    # Process
    fetcher = AdvancedTranscriptFetcher()
    start_time = time.time()
    
    logger.info(f"\nProcessing: batch_size={batch_size}, delay={delay}s")
    logger.info("Methods: Internal API → TimedText → Library → JSON Extract")
    logger.info("-" * 80)
    
    method_stats = {}
    
    for i, video in enumerate(videos):
        video_id = video['video_id']
        title = video['title'][:70]
        
        logger.info(f"\n[{i+1}/{len(videos)}] {title}")
        logger.info(f"  Video ID: {video_id}")
        
        # Get transcript
        transcript, method = fetcher.get_transcript(video_id)
        
        if transcript:
            # Stats
            method_stats[method] = method_stats.get(method, 0) + 1
            
            # Update DB
            if fetcher.update_video_transcript(video_id, transcript):
                logger.info(f"  ✅ SAVED ({len(transcript)} chars, method: {method})")
            else:
                logger.error(f"  ❌ DB save failed")
        else:
            logger.warning(f"  ⚠️  FAILED: All methods exhausted")
        
        # Batch delay
        if (i + 1) % batch_size == 0:
            logger.info(f"\n{'='*80}")
            logger.info(f"Progress: {i+1}/{len(videos)} ({(i+1)/len(videos)*100:.1f}%)")
            logger.info(f"Success: {fetcher.success_count}/{i+1} ({fetcher.success_count/(i+1)*100:.1f}%)")
            logger.info(f"{'='*80}\n")
            time.sleep(delay)
    
    # Summary
    elapsed = time.time() - start_time
    
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total: {len(videos)}")
    logger.info(f"Success: {fetcher.success_count} ({fetcher.success_count/len(videos)*100:.1f}%)")
    logger.info(f"Failed: {fetcher.fail_count}")
    logger.info(f"\nMethod breakdown:")
    for method, count in sorted(method_stats.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {method}: {count}")
    logger.info(f"\nTime: {elapsed/60:.1f} minutes")
    logger.info("=" * 80)
    
    return True


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Advanced transcript fetcher')
    parser.add_argument('-b', '--batch-size', type=int, default=10)
    parser.add_argument('-d', '--delay', type=float, default=2.0)
    parser.add_argument('-l', '--limit', type=int, default=None)
    
    args = parser.parse_args()
    
    try:
        DatabaseConnection.initialize_pool()
        fetch_transcripts_advanced(args.batch_size, args.delay, args.limit)
        return 0
    except KeyboardInterrupt:
        logger.info("\n\nInterrupted")
        return 1
    except Exception as e:
        logger.error(f"\n❌ Error: {e}", exc_info=True)
        return 1
    finally:
        DatabaseConnection.close_all_connections()


if __name__ == "__main__":
    sys.exit(main())