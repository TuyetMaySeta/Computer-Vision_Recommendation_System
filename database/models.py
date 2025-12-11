from database.connection import execute_query, execute_many
from utils.logger import get_logger

logger = get_logger(__name__)

# SQL để tạo tables
CREATE_VIDEOS_TABLE = """
CREATE TABLE IF NOT EXISTS videos (
    video_id VARCHAR(50) PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    channel_name VARCHAR(255),
    channel_id VARCHAR(50),
    published_date TIMESTAMP,
    view_count BIGINT DEFAULT 0,
    like_count INTEGER DEFAULT 0,
    duration INTEGER,
    tags TEXT[],
    category_id VARCHAR(10),
    transcript_text TEXT,
    video_url VARCHAR(255),
    thumbnail_url VARCHAR(500),
    language VARCHAR(10) DEFAULT 'en',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_videos_channel_id ON videos(channel_id);
CREATE INDEX IF NOT EXISTS idx_videos_published_date ON videos(published_date);
CREATE INDEX IF NOT EXISTS idx_videos_view_count ON videos(view_count);
"""

CREATE_CHANNELS_TABLE = """
CREATE TABLE IF NOT EXISTS channels (
    channel_id VARCHAR(50) PRIMARY KEY,
    channel_name VARCHAR(255) NOT NULL,
    subscriber_count BIGINT DEFAULT 0,
    video_count INTEGER DEFAULT 0,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_COLLECTION_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS collection_logs (
    id SERIAL PRIMARY KEY,
    collection_type VARCHAR(20) NOT NULL,
    query VARCHAR(255),
    videos_collected INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_logs_created_at ON collection_logs(created_at);
"""

def init_database():
    """Khởi tạo database với các tables cần thiết"""
    try:
        logger.info("Creating videos table...")
        execute_query(CREATE_VIDEOS_TABLE)
        
        logger.info("Creating channels table...")
        execute_query(CREATE_CHANNELS_TABLE)
        
        logger.info("Creating collection_logs table...")
        execute_query(CREATE_COLLECTION_LOGS_TABLE)
        
        logger.info("Database initialized successfully!")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

def insert_video(video_data):
    """
    Insert một video vào database
    
    Args:
        video_data: Dictionary chứa thông tin video
    
    Returns:
        True nếu thành công, False nếu thất bại
    """
    query = """
    INSERT INTO videos (
        video_id, title, description, channel_name, channel_id,
        published_date, view_count, like_count, duration, tags,
        category_id, transcript_text, video_url, thumbnail_url, language
    ) VALUES (
        %(video_id)s, %(title)s, %(description)s, %(channel_name)s, %(channel_id)s,
        %(published_date)s, %(view_count)s, %(like_count)s, %(duration)s, %(tags)s,
        %(category_id)s, %(transcript_text)s, %(video_url)s, %(thumbnail_url)s, %(language)s
    )
    ON CONFLICT (video_id) 
    DO UPDATE SET
        view_count = EXCLUDED.view_count,
        like_count = EXCLUDED.like_count,
        transcript_text = EXCLUDED.transcript_text,
        updated_at = CURRENT_TIMESTAMP
    """
    
    try:
        execute_query(query, video_data)
        return True
    except Exception as e:
        logger.error(f"Failed to insert video {video_data.get('video_id')}: {e}")
        return False

def insert_channel(channel_data):
    """Insert một channel vào database"""
    query = """
    INSERT INTO channels (
        channel_id, channel_name, subscriber_count, video_count, description
    ) VALUES (
        %(channel_id)s, %(channel_name)s, %(subscriber_count)s, 
        %(video_count)s, %(description)s
    )
    ON CONFLICT (channel_id)
    DO UPDATE SET
        channel_name = EXCLUDED.channel_name,
        subscriber_count = EXCLUDED.subscriber_count,
        video_count = EXCLUDED.video_count,
        description = EXCLUDED.description
    """
    
    try:
        execute_query(query, channel_data)
        return True
    except Exception as e:
        logger.error(f"Failed to insert channel {channel_data.get('channel_id')}: {e}")
        return False

def log_collection(collection_type, query, videos_collected, status='success', error_message=None):
    """Ghi log cho mỗi lần thu thập dữ liệu"""
    log_query = """
    INSERT INTO collection_logs (
        collection_type, query, videos_collected, status, error_message
    ) VALUES (%s, %s, %s, %s, %s)
    """
    
    try:
        execute_query(log_query, (collection_type, query, videos_collected, status, error_message))
        return True
    except Exception as e:
        logger.error(f"Failed to log collection: {e}")
        return False

def get_video_count():
    """Lấy tổng số video trong database"""
    query = "SELECT COUNT(*) as count FROM videos"
    result = execute_query(query, fetch=True)
    return result[0]['count'] if result else 0

def get_channel_count():
    """Lấy tổng số channel trong database"""
    query = "SELECT COUNT(*) as count FROM channels"
    result = execute_query(query, fetch=True)
    return result[0]['count'] if result else 0

def get_videos_by_channel(channel_id, limit=100):
    """Lấy danh sách video của một channel"""
    query = """
    SELECT * FROM videos 
    WHERE channel_id = %s 
    ORDER BY published_date DESC 
    LIMIT %s
    """
    return execute_query(query, (channel_id, limit), fetch=True)

def export_to_csv(output_file='data/exports/videos_export.csv'):
    """Export dữ liệu ra file CSV"""
    import csv
    
    query = "SELECT * FROM videos ORDER BY published_date DESC"
    videos = execute_query(query, fetch=True)
    
    if not videos:
        logger.warning("No videos to export")
        return False
    
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=videos[0].keys())
            writer.writeheader()
            writer.writerows(videos)
        
        logger.info(f"Exported {len(videos)} videos to {output_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to export to CSV: {e}")
        return False