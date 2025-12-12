#!/usr/bin/env python3
"""
Script để build embeddings database từ videos đã thu thập
UPDATED: Không yêu cầu transcript - dùng title + description
"""

import sys
import os

# Thêm thư mục gốc vào Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.models import execute_query
from database.connection import DatabaseConnection
from processors.embeddings import EmbeddingGenerator
from database.embeddings_store import EmbeddingsStore
from utils.logger import get_logger

logger = get_logger(__name__)

def load_videos_from_db():
    """
    Load tất cả videos từ PostgreSQL database
    UPDATED: Không yêu cầu transcript
    
    Returns:
        List of video dictionaries
    """
    logger.info("Loading videos from database...")
    
    query = """
    SELECT 
        video_id, title, description, channel_name, channel_id,
        published_date, view_count, like_count, duration, tags,
        transcript_text, video_url, thumbnail_url
    FROM videos
    WHERE title IS NOT NULL AND title != ''
    ORDER BY published_date DESC
    """
    
    videos = execute_query(query, fetch=True)
    
    # Convert to list of dicts
    videos_list = [dict(v) for v in videos]
    
    # Thống kê
    with_transcript = sum(1 for v in videos_list if v.get('transcript_text'))
    without_transcript = len(videos_list) - with_transcript
    
    logger.info(f"Loaded {len(videos_list)} videos from database")
    logger.info(f"  - With transcript: {with_transcript}")
    logger.info(f"  - Without transcript: {without_transcript} (will use title + description)")
    
    return videos_list

def build_embeddings(batch_size=50):
    """
    Build embeddings cho tất cả videos
    
    Args:
        batch_size: Số lượng videos xử lý mỗi batch
    """
    logger.info("=" * 60)
    logger.info("BUILDING EMBEDDINGS DATABASE")
    logger.info("=" * 60)
    
    # 1. Load videos từ database
    logger.info("\n[Step 1/3] Loading videos from database...")
    videos = load_videos_from_db()
    
    if not videos:
        logger.error("No videos found in database")
        logger.error("Please run data collection first:")
        logger.error("  python scripts/collect_by_keyword.py")
        logger.error("  OR")
        logger.error("  python scripts/collect_by_channel.py")
        return False
    
    # 2. Tạo embeddings
    logger.info(f"\n[Step 2/3] Creating embeddings for {len(videos)} videos...")
    logger.info(f"Processing in batches of {batch_size}...")
    logger.info("Note: Using title + description (transcript not required)")
    
    embedding_generator = EmbeddingGenerator(batch_size=batch_size)
    
    videos_with_embeddings = []
    
    for i in range(0, len(videos), batch_size):
        batch = videos[i:i + batch_size]
        logger.info(f"\nProcessing batch {i // batch_size + 1}/{(len(videos) - 1) // batch_size + 1}")
        
        # Process batch
        batch_results = embedding_generator.process_videos(batch)
        
        # Lọc chỉ lấy videos có embedding thành công
        successful = [v for v in batch_results if 'embedding' in v]
        videos_with_embeddings.extend(successful)
        
        logger.info(f"Batch complete: {len(successful)}/{len(batch)} successful")
    
    logger.info(f"\nTotal embeddings created: {len(videos_with_embeddings)}/{len(videos)}")
    
    if len(videos_with_embeddings) == 0:
        logger.error("No embeddings were created successfully!")
        return False
    
    # 3. Lưu embeddings
    logger.info("\n[Step 3/3] Saving embeddings to storage...")
    embeddings_store = EmbeddingsStore()
    
    success = embeddings_store.save_embeddings(videos_with_embeddings)
    
    if success:
        logger.info("✅ Embeddings saved successfully!")
        
        # Export to parquet (optional)
        logger.info("Exporting to parquet format...")
        embeddings_store.export_to_parquet()
        
        # Display statistics
        stats = embedding_generator.get_stats()
        logger.info("\n" + "=" * 60)
        logger.info("EMBEDDING STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Total requests: {stats['total_requests']:,}")
        logger.info(f"Model: {stats['model']}")
        logger.info(f"Cost: $0.00 (FREE - running locally!)")
        logger.info("=" * 60)
        
        # Display storage stats
        storage_stats = embeddings_store.get_stats()
        logger.info("\nDATABASE STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Total videos: {storage_stats['total_videos']:,}")
        logger.info(f"Total channels: {storage_stats['total_channels']}")
        logger.info(f"Average views: {storage_stats['avg_views']:,.0f}")
        logger.info(f"Average duration: {storage_stats['avg_duration']:.1f} minutes")
        logger.info("\nTop channels:")
        for channel, count in list(storage_stats['top_channels'].items())[:5]:
            logger.info(f"  - {channel}: {count} videos")
        logger.info("=" * 60)
        logger.info("\n✅ System ready! You can now search videos:")
        logger.info("   python scripts/search_videos.py -q \"your query here\"")
        
        return True
    else:
        logger.error("Failed to save embeddings")
        return False

def main():
    """Main function"""
    try:
        # Khởi tạo database connection
        DatabaseConnection.initialize_pool()
        
        # Build embeddings
        success = build_embeddings(batch_size=50)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("\nProcess interrupted by user")
        return 1
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1
        
    finally:
        DatabaseConnection.close_all_connections()

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)