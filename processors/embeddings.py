"""
Module để tạo embeddings cho video content
Sử dụng Sentence Transformers (MIỄN PHÍ, chạy local)
"""

from sentence_transformers import SentenceTransformer
import numpy as np
import time
from typing import List, Dict, Optional
from utils.logger import get_logger

logger = get_logger(__name__)

class EmbeddingGenerator:
    def __init__(self, model_name="all-MiniLM-L6-v2", batch_size=32):
        """
        Khởi tạo embedding generator với Sentence Transformers
        
        Args:
            model_name: Model name (all-MiniLM-L6-v2 là nhẹ và nhanh)
            batch_size: Số lượng text xử lý mỗi batch
        """
        logger.info(f"Loading model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
        self.batch_size = batch_size
        self.dimension = 384  # all-MiniLM-L6-v2 outputs 384-dim vectors
        
        self.total_requests = 0
        logger.info(f"Model loaded successfully! Embedding dimension: {self.dimension}")
    
    def clean_text(self, text: str) -> str:
        """
        Làm sạch text trước khi tạo embedding
        
        Args:
            text: Raw text
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Xóa ký tự đặc biệt
        import re
        text = re.sub(r'[^\w\s\-.,!?]', ' ', text)
        
        # Chuẩn hóa khoảng trắng
        text = ' '.join(text.split())
        
        # Giới hạn độ dài (model có giới hạn ~512 tokens)
        if len(text) > 5000:
            text = text[:5000]
        
        return text
    
    def combine_video_text(self, video_data: Dict) -> str:
        """
        Kết hợp title, description và transcript thành một văn bản
        UPDATED: Ưu tiên title + description nếu không có transcript
        
        Args:
            video_data: Dictionary chứa thông tin video
            
        Returns:
            Combined text
        """
        # Lấy các thành phần
        title = video_data.get('title', '')
        description = video_data.get('description', '')
        transcript = video_data.get('transcript_text', '')
        tags = video_data.get('tags', [])
        channel_name = video_data.get('channel_name', '')
        
        # Strategy: Title (×3) + Tags (×2) + Description (×2) + Transcript (×1)
        combined_parts = []
        
        # Title là quan trọng nhất
        if title:
            combined_parts.extend([title] * 3)
        
        # Tags (nếu có)
        if tags and isinstance(tags, list):
            tags_text = ' '.join(tags[:10])  # Top 10 tags
            combined_parts.extend([tags_text] * 2)
        
        # Description
        if description:
            # Lấy 1000 ký tự đầu của description
            desc_text = description[:1000]
            combined_parts.extend([desc_text] * 2)
        
        # Channel name (để tăng relevance với channel chất lượng)
        if channel_name:
            combined_parts.append(channel_name)
        
        # Transcript (nếu có)
        if transcript:
            # Cắt transcript nếu quá dài
            max_transcript_length = 2000
            if len(transcript) > max_transcript_length:
                transcript = transcript[:max_transcript_length]
            combined_parts.append(transcript)
        
        # Nếu không có gì cả, ít nhất có title
        if not combined_parts and title:
            combined_parts = [title]
        
        combined = ' '.join(combined_parts)
        return self.clean_text(combined)
    
    def create_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Tạo embedding cho một đoạn text
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector hoặc None nếu lỗi
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return None
        
        try:
            # Tạo embedding
            embedding = self.model.encode(
                text,
                convert_to_numpy=True,
                show_progress_bar=False,
                normalize_embeddings=True  # Normalize để tính cosine similarity nhanh hơn
            )
            
            self.total_requests += 1
            
            return embedding.astype(np.float32)
            
        except Exception as e:
            logger.error(f"Error creating embedding: {e}")
            return None
    
    def create_embeddings_batch(self, texts: List[str]) -> List[Optional[np.ndarray]]:
        """
        Tạo embeddings cho một batch texts
        
        Args:
            texts: List of texts
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        
        try:
            # Sentence Transformers có thể xử lý batch hiệu quả
            batch_embeddings = self.model.encode(
                texts,
                batch_size=self.batch_size,
                convert_to_numpy=True,
                show_progress_bar=True,
                normalize_embeddings=True
            )
            
            self.total_requests += len(texts)
            
            # Convert to list of arrays
            embeddings = [emb.astype(np.float32) for emb in batch_embeddings]
            
        except Exception as e:
            logger.error(f"Error creating batch embeddings: {e}")
            # Fallback to individual processing
            for text in texts:
                embedding = self.create_embedding(text)
                embeddings.append(embedding)
        
        return embeddings
    
    def process_videos(self, videos_data: List[Dict]) -> List[Dict]:
        """
        Xử lý danh sách videos và tạo embeddings
        UPDATED: Hoạt động tốt ngay cả khi không có transcript
        
        Args:
            videos_data: List of video dictionaries
            
        Returns:
            List of videos with embeddings added
        """
        logger.info(f"Processing {len(videos_data)} videos for embeddings...")
        
        # Thống kê
        with_transcript = sum(1 for v in videos_data if v.get('transcript_text'))
        without_transcript = len(videos_data) - with_transcript
        
        logger.info(f"Videos with transcript: {with_transcript}")
        logger.info(f"Videos without transcript: {without_transcript} (will use title + description)")
        
        # Chuẩn bị texts
        texts = []
        for video in videos_data:
            combined_text = self.combine_video_text(video)
            texts.append(combined_text)
        
        # Tạo embeddings batch (nhanh hơn nhiều)
        logger.info("Creating embeddings (this may take a few minutes)...")
        embeddings = self.create_embeddings_batch(texts)
        
        # Gắn embeddings vào videos
        results = []
        success_count = 0
        fail_count = 0
        
        for i, (video, embedding, text) in enumerate(zip(videos_data, embeddings, texts)):
            if embedding is not None:
                video['embedding'] = embedding
                video['full_text'] = text
                # Tạo summary từ description nếu có
                if not video.get('summary'):
                    desc = video.get('description', '')
                    video['summary'] = desc[:300] + '...' if len(desc) > 300 else desc
                success_count += 1
            else:
                fail_count += 1
                logger.warning(f"Failed to create embedding for video: {video.get('video_id')}")
            
            results.append(video)
        
        logger.info(f"Embedding generation complete. Success: {success_count}, Failed: {fail_count}")
        
        return results
    
    def get_stats(self) -> Dict:
        """Lấy thống kê"""
        return {
            'total_requests': self.total_requests,
            'total_tokens': 0,  # N/A for local models
            'estimated_cost': 0.0,  # FREE!
            'model': self.model_name
        }