"""
Module tính toán độ tương đồng và xếp hạng video
"""

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime
from typing import List, Dict, Optional
from utils.logger import get_logger

logger = get_logger(__name__)

class SimilarityCalculator:
    def __init__(self):
        """Khởi tạo similarity calculator"""
        self.quality_channels = {
            'Yannic Kilcher': 1.0,
            'Two Minute Papers': 1.0,
            'Sentdex': 1.0,
            'StatQuest with Josh Starmer': 1.0,
            '3Blue1Brown': 1.0,
            'Lex Fridman': 1.0,
            'Andrew Ng': 1.0,
            'deeplizard': 0.9,
            'CodeEmporium': 0.9,
            'Arxiv Insights': 0.9
        }
    
    def calculate_cosine_similarity(self, query_embedding: np.ndarray, 
                                   video_embeddings: np.ndarray) -> np.ndarray:
        """
        Tính cosine similarity giữa query và tất cả videos
        
        Args:
            query_embedding: Query embedding vector [1536]
            video_embeddings: Video embeddings matrix [N, 1536]
            
        Returns:
            Similarity scores array [N]
        """
        # Reshape query embedding nếu cần
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        # Tính cosine similarity
        similarities = cosine_similarity(query_embedding, video_embeddings)[0]
        
        return similarities
    
    def calculate_recency_score(self, published_date: datetime, 
                               max_age_years: float = 5.0) -> float:
        """
        Tính điểm dựa trên độ mới của video
        
        Args:
            published_date: Ngày publish video
            max_age_years: Tuổi tối đa để tính điểm (năm)
            
        Returns:
            Recency score từ 0 đến 1
        """
        if not published_date:
            return 0.5  # Default score
        
        # Tính số ngày từ khi publish
        days_since_publish = (datetime.now() - published_date).days
        
        # Tính score (decay theo thời gian)
        # Formula: 1 / (1 + days/365)
        recency_score = 1.0 / (1.0 + days_since_publish / 365.0)
        
        # Nếu quá cũ (> max_age_years), giảm điểm mạnh
        if days_since_publish > max_age_years * 365:
            recency_score *= 0.5
        
        return recency_score
    
    def calculate_popularity_score(self, view_count: int, 
                                  max_views: int = 10000000) -> float:
        """
        Tính điểm dựa trên popularity (view count)
        
        Args:
            view_count: Số lượt xem
            max_views: Số view tối đa để normalize
            
        Returns:
            Popularity score từ 0 đến 1
        """
        if view_count <= 0:
            return 0.0
        
        # Log scale để tránh bias với video có view cực cao
        import math
        score = math.log(view_count + 1) / math.log(max_views + 1)
        
        return min(score, 1.0)
    
    def get_channel_quality_score(self, channel_name: str) -> float:
        """
        Lấy quality score của channel
        
        Args:
            channel_name: Tên channel
            
        Returns:
            Quality score từ 0.5 đến 1.0
        """
        return self.quality_channels.get(channel_name, 0.5)
    
    def calculate_final_score(self, video: Dict, similarity_score: float,
                             max_views: int = 10000000) -> float:
        """
        Tính final score kết hợp nhiều yếu tố
        
        Args:
            video: Video dictionary
            similarity_score: Cosine similarity score
            max_views: Max views để normalize
            
        Returns:
            Final score
        """
        # Weights
        SIMILARITY_WEIGHT = 0.70
        POPULARITY_WEIGHT = 0.15
        RECENCY_WEIGHT = 0.10
        CHANNEL_WEIGHT = 0.05
        
        # Tính các component scores
        recency_score = self.calculate_recency_score(video.get('published_date'))
        popularity_score = self.calculate_popularity_score(
            video.get('view_count', 0), 
            max_views
        )
        channel_score = self.get_channel_quality_score(video.get('channel_name', ''))
        
        # Tính final score
        final_score = (
            SIMILARITY_WEIGHT * similarity_score +
            POPULARITY_WEIGHT * popularity_score +
            RECENCY_WEIGHT * recency_score +
            CHANNEL_WEIGHT * channel_score
        )
        
        return final_score
    
    def filter_videos(self, videos: List[Dict]) -> List[Dict]:
        """
        Lọc videos theo các tiêu chí cơ bản
        
        Args:
            videos: List of video dictionaries
            
        Returns:
            Filtered list of videos
        """
        filtered = []
        
        for video in videos:
            # Loại bỏ video quá cũ (>5 năm)
            if video.get('published_date'):
                days_old = (datetime.now() - video['published_date']).days
                if days_old > 5 * 365:
                    continue
            
            # Loại bỏ video view quá thấp (<1000)
            if video.get('view_count', 0) < 1000:
                continue
            
            # Loại bỏ video quá ngắn (<2 min) hoặc quá dài (>3 hours)
            duration = video.get('duration', 0)
            if duration > 0 and (duration < 120 or duration > 10800):
                continue
            
            filtered.append(video)
        
        logger.info(f"Filtered: {len(videos)} -> {len(filtered)} videos")
        return filtered
    
    def ensure_diversity(self, ranked_videos: List[Dict], max_per_channel: int = 2) -> List[Dict]:
        """
        Đảm bảo diversity - không quá nhiều video từ cùng channel
        
        Args:
            ranked_videos: Danh sách videos đã được rank
            max_per_channel: Số video tối đa từ cùng một channel
            
        Returns:
            Diverse list of videos
        """
        diverse_videos = []
        channel_count = {}
        
        for video in ranked_videos:
            channel = video.get('channel_name', 'Unknown')
            
            # Đếm số video từ channel này
            count = channel_count.get(channel, 0)
            
            if count < max_per_channel:
                diverse_videos.append(video)
                channel_count[channel] = count + 1
        
        logger.info(f"Diversity filter: {len(ranked_videos)} -> {len(diverse_videos)} videos")
        return diverse_videos
    
    def rank_videos(self, query_embedding: np.ndarray, 
                   videos: List[Dict],
                   top_k: int = 5) -> List[Dict]:
        """
        Rank videos và trả về top K
        
        Args:
            query_embedding: Query embedding vector
            videos: List of video dictionaries (with embeddings)
            top_k: Số lượng kết quả trả về
            
        Returns:
            Top K ranked videos
        """
        logger.info(f"Ranking {len(videos)} videos...")
        
        # Filter videos
        filtered_videos = self.filter_videos(videos)
        
        if not filtered_videos:
            logger.warning("No videos after filtering")
            return []
        
        # Trích xuất embeddings
        video_embeddings = np.array([v['embedding'] for v in filtered_videos])
        
        # Tính similarity scores
        similarity_scores = self.calculate_cosine_similarity(
            query_embedding, 
            video_embeddings
        )
        
        # Tìm max views để normalize
        max_views = max([v.get('view_count', 0) for v in filtered_videos])
        
        # Tính final scores
        for i, video in enumerate(filtered_videos):
            video['similarity_score'] = float(similarity_scores[i])
            video['final_score'] = self.calculate_final_score(
                video, 
                similarity_scores[i],
                max_views
            )
        
        # Sort theo final score
        ranked = sorted(filtered_videos, key=lambda x: x['final_score'], reverse=True)
        
        # Ensure diversity
        diverse_ranked = self.ensure_diversity(ranked, max_per_channel=2)
        
        # Lấy top K
        top_videos = diverse_ranked[:top_k]
        
        logger.info(f"Top {len(top_videos)} videos selected")
        
        # Thêm rank
        for i, video in enumerate(top_videos):
            video['rank'] = i + 1
        
        return top_videos
    
    def generate_relevance_explanation(self, video: Dict, query_text: str) -> str:
        """
        Tạo explanation về tại sao video này relevant
        
        Args:
            video: Video dictionary
            query_text: Original query text
            
        Returns:
            Explanation string
        """
        # Extract keywords từ query
        query_words = set(query_text.lower().split())
        
        # Extract keywords từ video title
        title_words = set(video.get('title', '').lower().split())
        
        # Tìm common keywords
        common_words = query_words.intersection(title_words)
        common_words = [w for w in common_words if len(w) > 3]  # Chỉ lấy từ dài
        
        if common_words:
            keywords = ', '.join(list(common_words)[:3])
            explanation = f"Discusses {keywords}, directly matching your query"
        else:
            explanation = f"Highly relevant to '{query_text[:50]}...' based on content similarity"
        
        # Thêm thông tin về channel nếu là quality channel
        channel = video.get('channel_name', '')
        if channel in self.quality_channels:
            explanation += f" from trusted channel {channel}"
        
        return explanation
    
    def format_results(self, ranked_videos: List[Dict], query_text: str) -> List[Dict]:
        """
        Format kết quả để trả về cho user
        
        Args:
            ranked_videos: Danh sách videos đã ranked
            query_text: Original query text
            
        Returns:
            Formatted results
        """
        results = []
        
        for video in ranked_videos:
            # Format duration
            duration_sec = video.get('duration', 0)
            duration_str = f"{duration_sec // 60}:{duration_sec % 60:02d}"
            
            # Format view count
            view_count = video.get('view_count', 0)
            if view_count >= 1000000:
                view_str = f"{view_count / 1000000:.1f}M"
            elif view_count >= 1000:
                view_str = f"{view_count / 1000:.1f}K"
            else:
                view_str = str(view_count)
            
            # Generate relevance explanation
            explanation = self.generate_relevance_explanation(video, query_text)
            
            result = {
                'rank': video['rank'],
                'video_id': video['video_id'],
                'title': video['title'],
                'channel': video['channel_name'],
                'url': video['video_url'],
                'thumbnail': video.get('thumbnail_url', ''),
                'duration': duration_str,
                'view_count': view_str,
                'published_date': video['published_date'].strftime('%Y-%m-%d') if video.get('published_date') else 'Unknown',
                'similarity_score': round(video['similarity_score'], 3),
                'final_score': round(video['final_score'], 3),
                'summary': video.get('summary', video.get('description', '')[:200] + '...'),
                'why_relevant': explanation
            }
            
            results.append(result)
        
        return results