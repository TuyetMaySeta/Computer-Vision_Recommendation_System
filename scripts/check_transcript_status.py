#!/usr/bin/env python3
"""
Script để kiểm tra trạng thái transcripts trong database
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.models import execute_query
from database.connection import DatabaseConnection
from utils.logger import get_logger

logger = get_logger(__name__)


def check_transcript_status():
    """Check and display transcript statistics"""
    
    logger.info("=" * 80)
    logger.info("TRANSCRIPT STATUS REPORT")
    logger.info("=" * 80)
    
    # Overall stats
    query_overall = """
    SELECT 
        COUNT(*) as total_videos,
        COUNT(CASE WHEN transcript_text IS NOT NULL AND transcript_text != '' THEN 1 END) as with_transcript,
        COUNT(CASE WHEN transcript_text IS NULL OR transcript_text = '' THEN 1 END) as without_transcript
    FROM videos
    """
    
    overall = execute_query(query_overall, fetch=True)[0]
    
    logger.info("\n📊 Overall Statistics:")
    logger.info(f"  Total videos: {overall['total_videos']}")
    logger.info(f"  With transcript: {overall['with_transcript']} ({overall['with_transcript']/overall['total_videos']*100:.1f}%)")
    logger.info(f"  Without transcript: {overall['without_transcript']} ({overall['without_transcript']/overall['total_videos']*100:.1f}%)")
    
    # By channel
    query_channel = """
    SELECT 
        channel_name,
        COUNT(*) as total,
        COUNT(CASE WHEN transcript_text IS NOT NULL AND transcript_text != '' THEN 1 END) as with_transcript,
        ROUND(
            COUNT(CASE WHEN transcript_text IS NOT NULL AND transcript_text != '' THEN 1 END)::numeric / 
            COUNT(*)::numeric * 100, 
            1
        ) as percentage
    FROM videos
    GROUP BY channel_name
    ORDER BY total DESC
    LIMIT 10
    """
    
    by_channel = execute_query(query_channel, fetch=True)
    
    logger.info("\n📺 Top 10 Channels:")
    logger.info(f"{'Channel':<30} {'Total':>8} {'Transcripts':>12} {'%':>8}")
    logger.info("-" * 80)
    
    for row in by_channel:
        logger.info(
            f"{row['channel_name']:<30} "
            f"{row['total']:>8} "
            f"{row['with_transcript']:>12} "
            f"{row['percentage']:>7.1f}%"
        )
    
    # Sample videos without transcripts
    query_samples = """
    SELECT video_id, title, channel_name, view_count
    FROM videos
    WHERE transcript_text IS NULL OR transcript_text = ''
    ORDER BY view_count DESC
    LIMIT 5
    """
    
    samples = execute_query(query_samples, fetch=True)
    
    if samples:
        logger.info("\n🎥 Sample Videos WITHOUT Transcripts (Top 5 by views):")
        for i, video in enumerate(samples, 1):
            logger.info(f"\n{i}. {video['title']}")
            logger.info(f"   ID: {video['video_id']}")
            logger.info(f"   Channel: {video['channel_name']}")
            logger.info(f"   Views: {video['view_count']:,}")
            logger.info(f"   URL: https://www.youtube.com/watch?v={video['video_id']}")
    
    # Transcript length stats
    query_length = """
    SELECT 
        AVG(LENGTH(transcript_text)) as avg_length,
        MIN(LENGTH(transcript_text)) as min_length,
        MAX(LENGTH(transcript_text)) as max_length
    FROM videos
    WHERE transcript_text IS NOT NULL AND transcript_text != ''
    """
    
    length_stats = execute_query(query_length, fetch=True)[0]
    
    if length_stats['avg_length']:
        logger.info("\n📝 Transcript Length Statistics:")
        logger.info(f"  Average: {length_stats['avg_length']:.0f} characters")
        logger.info(f"  Minimum: {length_stats['min_length']} characters")
        logger.info(f"  Maximum: {length_stats['max_length']:,} characters")
    
    logger.info("\n" + "=" * 80)
    
    # Recommendations
    if overall['without_transcript'] > 0:
        logger.info("\n💡 Recommendations:")
        logger.info("  Run the following command to fetch missing transcripts:")
        logger.info("  python scripts/fetch_missing_transcripts.py")
        logger.info("\n  Options:")
        logger.info("    -b 10    Process in batches of 10")
        logger.info("    -d 2.0   Wait 2 seconds between batches")
        logger.info("    -l 50    Process only 50 videos")
    else:
        logger.info("\n✅ All videos have transcripts!")


def main():
    try:
        DatabaseConnection.initialize_pool()
        check_transcript_status()
        return 0
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1
    finally:
        DatabaseConnection.close_all_connections()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)