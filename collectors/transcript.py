from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled, 
    NoTranscriptFound,
    VideoUnavailable
)
import time
from utils.logger import get_logger

logger = get_logger(__name__)

class TranscriptCollector:
    def __init__(self):
        self.success_count = 0
        self.fail_count = 0
    
    def get_transcript(self, video_id, languages=['en', 'en-US', 'en-GB']):
        """
        Lấy transcript/phụ đề của video
        
        Args:
            video_id: YouTube video ID
            languages: List các ngôn ngữ ưu tiên
        
        Returns:
            String chứa transcript text hoặc None nếu không có
        """
        try:
            # Lấy transcript
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Thử tìm transcript thủ công trước (chất lượng tốt hơn)
            try:
                transcript = transcript_list.find_manually_created_transcript(languages)
            except NoTranscriptFound:
                # Nếu không có thủ công, dùng auto-generated
                try:
                    transcript = transcript_list.find_generated_transcript(languages)
                except NoTranscriptFound:
                    logger.warning(f"No transcript found for video: {video_id}")
                    self.fail_count += 1
                    return None
            
            # Fetch transcript data
            transcript_data = transcript.fetch()
            
            # Ghép các đoạn transcript lại thành text
            full_text = ' '.join([entry['text'] for entry in transcript_data])
            
            self.success_count += 1
            return full_text
            
        except TranscriptsDisabled:
            logger.warning(f"Transcripts disabled for video: {video_id}")
            self.fail_count += 1
            return None
        
        except VideoUnavailable:
            logger.warning(f"Video unavailable: {video_id}")
            self.fail_count += 1
            return None
        
        except Exception as e:
            logger.error(f"Error getting transcript for {video_id}: {e}")
            self.fail_count += 1
            return None
    
    def get_transcripts_batch(self, video_ids, delay=0.5):
        """
        Lấy transcript cho nhiều video
        
        Args:
            video_ids: List of video IDs
            delay: Delay giữa các request (seconds)
        
        Returns:
            Dictionary {video_id: transcript_text}
        """
        transcripts = {}
        
        for i, video_id in enumerate(video_ids):
            transcript = self.get_transcript(video_id)
            transcripts[video_id] = transcript
            
            # Log progress
            if (i + 1) % 10 == 0:
                logger.info(f"Processed {i + 1}/{len(video_ids)} transcripts")
            
            # Delay để tránh rate limit
            time.sleep(delay)
        
        logger.info(f"Transcript collection complete. Success: {self.success_count}, Failed: {self.fail_count}")
        return transcripts
    
    def get_stats(self):
        """Lấy thống kê"""
        return {
            'success': self.success_count,
            'failed': self.fail_count,
            'total': self.success_count + self.fail_count,
            'success_rate': self.success_count / (self.success_count + self.fail_count) * 100 
                           if (self.success_count + self.fail_count) > 0 else 0
        }