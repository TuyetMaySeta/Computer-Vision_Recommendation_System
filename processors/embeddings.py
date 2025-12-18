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

# processors/embeddings.py
class EmbeddingGenerator:
    def __init__(self, model_name="all-mpnet-base-v2", batch_size=32):
        """
        UPGRADE: Sử dụng model tốt hơn
        
        Model options (theo thứ tự chất lượng):
        1. "all-mpnet-base-v2" (768 dims) - TỐT NHẤT cho semantic search
        2. "all-MiniLM-L12-v2" (384 dims) - Cân bằng speed/quality
        3. "all-MiniLM-L6-v2" (384 dims) - Nhanh nhưng kém hơn
        """
        logger.info(f"Loading model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
        self.batch_size = batch_size
        self.dimension = self.model.get_sentence_embedding_dimension()
    
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
    # processors/embeddings.py - ADVANCED VERSION
    def chunk_transcript_semantic(self, transcript: str, max_chunk_size=512) -> list:
        """
        Chia transcript thành chunks semantic (theo câu)
        """
        import re
        
        # Split by sentences
        sentences = re.split(r'[.!?]+', transcript)
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_length = len(sentence.split())
            
            if current_length + sentence_length > max_chunk_size:
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_length = sentence_length
            else:
                current_chunk.append(sentence)
                current_length += sentence_length
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks

    def process_videos_with_chunking(self, videos_data: List[Dict]) -> List[Dict]:
        """
        Process với chunking - tạo multiple embeddings per video
        """
        for video in videos_data:
            transcript = video.get('transcript_text', '')
            
            if transcript and len(transcript) > 10000:
                # Chunk transcript
                chunks = self.chunk_transcript_semantic(transcript)
                
                # Create embedding for each chunk
                chunk_embeddings = self.create_embeddings_batch(chunks)
                
                # Average pooling (hoặc max pooling)
                video['embedding'] = np.mean(chunk_embeddings, axis=0)
            else:
                # Normal processing
                text = self.combine_video_text(video)
                video['embedding'] = self.create_embedding(text)
        
        return videos_data
    def combine_video_text(self, video_data: Dict) -> str:
        
        # Lấy các thành phần
        title = video_data.get('title', '')
        description = video_data.get('description', '')
        transcript = video_data.get('transcript_text', '')
        tags = video_data.get('tags', [])
        channel_name = video_data.get('channel_name', '')
        
        combined_parts = []
        
        # ===== THAY ĐỔI CHÍNH =====
        
        # 1. TRANSCRIPT là quan trọng NHẤT (×5) - TĂNG TỪ ×1
        if transcript and len(transcript) >= 100:
            # Thay vì cắt 2000 chars, sử dụng 5000-8000 chars
            max_transcript_length = 8000  # Tăng từ 2000
            
            # Intelligent chunking: Lấy đều từ đầu, giữa, cuối
            if len(transcript) > max_transcript_length:
                chunk_size = max_transcript_length // 3
                start = transcript[:chunk_size]
                middle_start = len(transcript) // 2 - chunk_size // 2
                middle = transcript[middle_start:middle_start + chunk_size]
                end = transcript[-chunk_size:]
                transcript_text = f"{start} {middle} {end}"
            else:
                transcript_text = transcript
            
            # Weight ×5 thay vì ×1
            combined_parts.extend([transcript_text] * 5)
        
        # 2. Title (×3) - giữ nguyên
        if title:
            combined_parts.extend([title] * 3)
        
        # 3. Description (×2) - tăng limit
        if description:
            desc_text = description[:2000]  # Tăng từ 1000
            combined_parts.extend([desc_text] * 2)
        
        # 4. Tags (×2) - giữ nguyên
        if tags and isinstance(tags, list):
            tags_text = ' '.join(tags[:15])  # Tăng từ 10
            combined_parts.extend([tags_text] * 2)
        
        # 5. Channel (×1)
        if channel_name:
            combined_parts.append(channel_name)
        
        # Fallback nếu không có transcript
        if not transcript and not combined_parts:
            combined_parts = [title] * 5 if title else []
        
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