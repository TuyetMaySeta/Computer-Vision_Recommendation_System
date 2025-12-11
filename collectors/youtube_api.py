from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import isodate
from datetime import datetime
import time
from config.settings import (
    YOUTUBE_API_KEY, 
    YOUTUBE_API_SERVICE_NAME, 
    YOUTUBE_API_VERSION,
    MAX_RESULTS_PER_QUERY,
    SLEEP_BETWEEN_REQUESTS
)
from utils.logger import get_logger

logger = get_logger(__name__)

class YouTubeAPICollector:
    def __init__(self):
        self.youtube = build(
            YOUTUBE_API_SERVICE_NAME, 
            YOUTUBE_API_VERSION, 
            developerKey=YOUTUBE_API_KEY
        )
        self.quota_used = 0
    
    def search_videos(self, query, max_results=50, order='relevance'):
        """
        Tìm kiếm video theo keyword
        
        Args:
            query: Từ khóa tìm kiếm
            max_results: Số lượng kết quả tối đa
            order: Thứ tự sắp xếp (relevance, date, viewCount, rating)
        
        Returns:
            List of video IDs
        """
        video_ids = []
        next_page_token = None
        
        try:
            while len(video_ids) < max_results:
                request = self.youtube.search().list(
                    part='id',
                    q=query,
                    type='video',
                    maxResults=min(50, max_results - len(video_ids)),
                    order=order,
                    pageToken=next_page_token,
                    videoDuration='medium',  # Lọc video có độ dài vừa phải
                    relevanceLanguage='en'
                )
                
                response = request.execute()
                self.quota_used += 100  # Search costs 100 quota units
                
                for item in response.get('items', []):
                    if item['id']['kind'] == 'youtube#video':
                        video_ids.append(item['id']['videoId'])
                
                next_page_token = response.get('nextPageToken')
                
                if not next_page_token:
                    break
                
                time.sleep(SLEEP_BETWEEN_REQUESTS)
            
            logger.info(f"Found {len(video_ids)} videos for query: {query}")
            return video_ids
            
        except HttpError as e:
            logger.error(f"YouTube API error for query '{query}': {e}")
            return video_ids
    
    def get_video_details(self, video_ids):
        """
        Lấy thông tin chi tiết của các video
        
        Args:
            video_ids: List of video IDs
        
        Returns:
            List of video details dictionaries
        """
        if not video_ids:
            return []
        
        videos_data = []
        
        # YouTube API chỉ cho phép lấy tối đa 50 video mỗi lần
        for i in range(0, len(video_ids), 50):
            batch_ids = video_ids[i:i+50]
            
            try:
                request = self.youtube.videos().list(
                    part='snippet,contentDetails,statistics',
                    id=','.join(batch_ids)
                )
                
                response = request.execute()
                self.quota_used += 1  # Videos.list costs 1 quota unit per video
                
                for item in response.get('items', []):
                    video_data = self._parse_video_item(item)
                    videos_data.append(video_data)
                
                time.sleep(SLEEP_BETWEEN_REQUESTS)
                
            except HttpError as e:
                logger.error(f"Error fetching video details: {e}")
                continue
        
        logger.info(f"Retrieved details for {len(videos_data)} videos")
        return videos_data
    
    def _parse_video_item(self, item):
        """Parse video item từ API response"""
        snippet = item.get('snippet', {})
        statistics = item.get('statistics', {})
        content_details = item.get('contentDetails', {})
        
        # Parse duration từ ISO 8601 format (PT15M33S) sang seconds
        duration_iso = content_details.get('duration', 'PT0S')
        duration_seconds = int(isodate.parse_duration(duration_iso).total_seconds())
        
        # Parse published date
        published_at = snippet.get('publishedAt', '')
        try:
            published_date = datetime.strptime(published_at, '%Y-%m-%dT%H:%M:%SZ')
        except:
            published_date = None
        
        video_data = {
            'video_id': item['id'],
            'title': snippet.get('title', ''),
            'description': snippet.get('description', ''),
            'channel_name': snippet.get('channelTitle', ''),
            'channel_id': snippet.get('channelId', ''),
            'published_date': published_date,
            'view_count': int(statistics.get('viewCount', 0)),
            'like_count': int(statistics.get('likeCount', 0)),
            'duration': duration_seconds,
            'tags': snippet.get('tags', []),
            'category_id': snippet.get('categoryId', ''),
            'video_url': f"https://www.youtube.com/watch?v={item['id']}",
            'thumbnail_url': snippet.get('thumbnails', {}).get('high', {}).get('url', ''),
            'language': snippet.get('defaultLanguage', 'en'),
            'transcript_text': None  # Sẽ được thu thập riêng
        }
        
        return video_data
    
    def get_channel_videos(self, channel_name, max_results=100):
        """
        Lấy tất cả video từ một channel
        
        Args:
            channel_name: Tên channel
            max_results: Số lượng video tối đa
        
        Returns:
            List of video IDs
        """
        try:
            # Tìm channel ID từ tên channel
            search_request = self.youtube.search().list(
                part='id',
                q=channel_name,
                type='channel',
                maxResults=1
            )
            search_response = search_request.execute()
            self.quota_used += 100
            
            if not search_response.get('items'):
                logger.warning(f"Channel not found: {channel_name}")
                return []
            
            channel_id = search_response['items'][0]['id']['channelId']
            
            # Lấy videos từ channel
            video_ids = []
            next_page_token = None
            
            while len(video_ids) < max_results:
                request = self.youtube.search().list(
                    part='id',
                    channelId=channel_id,
                    type='video',
                    maxResults=min(50, max_results - len(video_ids)),
                    order='date',
                    pageToken=next_page_token
                )
                
                response = request.execute()
                self.quota_used += 100
                
                for item in response.get('items', []):
                    if item['id']['kind'] == 'youtube#video':
                        video_ids.append(item['id']['videoId'])
                
                next_page_token = response.get('nextPageToken')
                
                if not next_page_token:
                    break
                
                time.sleep(SLEEP_BETWEEN_REQUESTS)
            
            logger.info(f"Found {len(video_ids)} videos from channel: {channel_name}")
            return video_ids
            
        except HttpError as e:
            logger.error(f"Error fetching channel videos for '{channel_name}': {e}")
            return []
    
    def get_channel_info(self, channel_id):
        """Lấy thông tin channel"""
        try:
            request = self.youtube.channels().list(
                part='snippet,statistics',
                id=channel_id
            )
            
            response = request.execute()
            self.quota_used += 1
            
            if not response.get('items'):
                return None
            
            item = response['items'][0]
            snippet = item.get('snippet', {})
            statistics = item.get('statistics', {})
            
            channel_data = {
                'channel_id': channel_id,
                'channel_name': snippet.get('title', ''),
                'subscriber_count': int(statistics.get('subscriberCount', 0)),
                'video_count': int(statistics.get('videoCount', 0)),
                'description': snippet.get('description', '')
            }
            
            return channel_data
            
        except HttpError as e:
            logger.error(f"Error fetching channel info for '{channel_id}': {e}")
            return None
    
    def get_quota_used(self):
        """Lấy quota đã sử dụng"""
        return self.quota_used