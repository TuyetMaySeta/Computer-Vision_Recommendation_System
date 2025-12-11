#!/usr/bin/env python3
"""
Script để thu thập video theo keyword
"""

import sys
import os
from datetime import datetime

# Thêm thư mục gốc vào Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from collectors.youtube_api import YouTubeAPICollector
from collectors.transcript import TranscriptCollector
from database.models import insert_video, insert_channel, log_collection, get_video_count
from database.connection import DatabaseConnection
from config.settings import DEFAULT_KEYWORDS, MAX_VIDEOS_PER_KEYWORD
from utils.logger import get_logger

logger = get_logger(__name__)

def collect_videos_by_keywords(keywords=None, max_per_keyword=MAX_VIDEOS_PER_KEYWORD):
    """
    Thu thập video theo danh sách keywords
    
    Args:
        keywords: List of keywords (None để dùng default)
        max_per_keyword: Số video tối đa cho mỗi keyword
    """
    if keywords is None:
        keywords = DEFAULT_KEYWORDS
    
    logger.info("=" * 60)
    logger.info("Starting video collection by keywords")
    logger.info("=" * 60)
    logger.info(f"Keywords: {keywords}")
    logger.info(f"Max videos per keyword: {max_per_keyword}")
    
    # Khởi tạo collectors
    youtube_collector = YouTubeAPICollector()
    transcript_collector = TranscriptCollector()
    
    total_videos_collected = 0
    total_videos_saved = 0
    
    for keyword in keywords:
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing keyword: '{keyword}'")
        logger.info(f"{'='*60}")
        
        try:
            # 1. Tìm kiếm video
            logger.info("Searching for videos...")
            video_ids = youtube_collector.search_videos(
                query=keyword,
                max_results=max_per_keyword,
                order='relevance'
            )
            
            if not video_ids:
                logger.warning(f"No videos found for keyword: {keyword}")
                log_collection('keyword', keyword, 0, 'no_results')
                continue
            
            total_videos_collected += len(video_ids)
            
            # 2. Lấy thông tin chi tiết video
            logger.info("Fetching video details...")
            videos_data = youtube_collector.get_video_details(video_ids)
            
            # 3. Lấy transcript
            logger.info("Fetching transcripts...")
            transcripts = transcript_collector.get_transcripts_batch(video_ids)
            
            # 4. Lưu vào database
            logger.info("Saving to database...")
            saved_count = 0
            
            for video_data in videos_data:
                video_id = video_data['video_id']
                
                # Thêm transcript vào video data
                video_data['transcript_text'] = transcripts.get(video_id)
                
                # Lưu video
                if insert_video(video_data):
                    saved_count += 1
                    
                    # Lưu channel info (nếu chưa có)
                    channel_id = video_data['channel_id']
                    channel_info = youtube_collector.get_channel_info(channel_id)
                    if channel_info:
                        insert_channel(channel_info)
            
            total_videos_saved += saved_count
            
            # Log kết quả
            logger.info(f"Saved {saved_count}/{len(videos_data)} videos for keyword: {keyword}")
            log_collection('keyword', keyword, saved_count, 'success')
            
        except Exception as e:
            logger.error(f"Error processing keyword '{keyword}': {e}")
            log_collection('keyword', keyword, 0, 'error', str(e))
    
    # Thống kê cuối cùng
    logger.info("\n" + "=" * 60)
    logger.info("COLLECTION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total keywords processed: {len(keywords)}")
    logger.info(f"Total videos found: {total_videos_collected}")
    logger.info(f"Total videos saved: {total_videos_saved}")
    logger.info(f"Total videos in database: {get_video_count()}")
    logger.info(f"YouTube API quota used: {youtube_collector.get_quota_used()}")
    
    transcript_stats = transcript_collector.get_stats()
    logger.info(f"Transcript success rate: {transcript_stats['success_rate']:.1f}%")
    logger.info("=" * 60)

def main():
    """Main function"""
    try:
        # Khởi tạo database connection
        DatabaseConnection.initialize_pool()
        
        # Thu thập dữ liệu
        collect_videos_by_keywords()
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("\nCollection interrupted by user")
        return 1
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1
        
    finally:
        DatabaseConnection.close_all_connections()

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)