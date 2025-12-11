#!/usr/bin/env python3
"""
Script để thu thập video từ các channel chất lượng cao
"""

import sys
import os

# Thêm thư mục gốc vào Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from collectors.youtube_api import YouTubeAPICollector
from collectors.transcript import TranscriptCollector
from database.models import insert_video, insert_channel, log_collection, get_video_count
from database.connection import DatabaseConnection
from config.settings import QUALITY_CHANNELS, MAX_VIDEOS_PER_CHANNEL
from utils.logger import get_logger

logger = get_logger(__name__)

def collect_videos_by_channels(channel_names=None, max_per_channel=MAX_VIDEOS_PER_CHANNEL):
    """
    Thu thập video từ danh sách channels
    
    Args:
        channel_names: List of channel names (None để dùng default)
        max_per_channel: Số video tối đa cho mỗi channel
    """
    if channel_names is None:
        channel_names = QUALITY_CHANNELS
    
    logger.info("=" * 60)
    logger.info("Starting video collection by channels")
    logger.info("=" * 60)
    logger.info(f"Channels: {channel_names}")
    logger.info(f"Max videos per channel: {max_per_channel}")
    
    # Khởi tạo collectors
    youtube_collector = YouTubeAPICollector()
    transcript_collector = TranscriptCollector()
    
    total_videos_collected = 0
    total_videos_saved = 0
    
    for channel_name in channel_names:
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing channel: '{channel_name}'")
        logger.info(f"{'='*60}")
        
        try:
            # 1. Lấy danh sách video từ channel
            logger.info("Fetching videos from channel...")
            video_ids = youtube_collector.get_channel_videos(
                channel_name=channel_name,
                max_results=max_per_channel
            )
            
            if not video_ids:
                logger.warning(f"No videos found for channel: {channel_name}")
                log_collection('channel', channel_name, 0, 'no_results')
                continue
            
            total_videos_collected += len(video_ids)
            
            # 2. Lấy thông tin chi tiết video
            logger.info("Fetching video details...")
            videos_data = youtube_collector.get_video_details(video_ids)
            
            # 3. Lưu channel info
            if videos_data:
                channel_id = videos_data[0]['channel_id']
                channel_info = youtube_collector.get_channel_info(channel_id)
                if channel_info:
                    insert_channel(channel_info)
                    logger.info(f"Channel info: {channel_info['subscriber_count']:,} subscribers, {channel_info['video_count']:,} videos")
            
            # 4. Lấy transcript
            logger.info("Fetching transcripts...")
            transcripts = transcript_collector.get_transcripts_batch(video_ids)
            
            # 5. Lưu vào database
            logger.info("Saving to database...")
            saved_count = 0
            
            for video_data in videos_data:
                video_id = video_data['video_id']
                
                # Thêm transcript vào video data
                video_data['transcript_text'] = transcripts.get(video_id)
                
                # Lưu video
                if insert_video(video_data):
                    saved_count += 1
            
            total_videos_saved += saved_count
            
            # Log kết quả
            logger.info(f"Saved {saved_count}/{len(videos_data)} videos from channel: {channel_name}")
            log_collection('channel', channel_name, saved_count, 'success')
            
        except Exception as e:
            logger.error(f"Error processing channel '{channel_name}': {e}")
            log_collection('channel', channel_name, 0, 'error', str(e))
    
    # Thống kê cuối cùng
    logger.info("\n" + "=" * 60)
    logger.info("COLLECTION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total channels processed: {len(channel_names)}")
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
        collect_videos_by_channels()
        
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