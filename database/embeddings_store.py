"""
Module để lưu trữ và quản lý embeddings
Sử dụng pickle/parquet để lưu trữ local
"""

import pickle
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional
from utils.logger import get_logger

logger = get_logger(__name__)

class EmbeddingsStore:
    def __init__(self, storage_path='data/embeddings/videos_embeddings.pkl'):
        """
        Khởi tạo embeddings store
        
        Args:
            storage_path: Đường dẫn lưu embeddings
        """
        self.storage_path = storage_path
        self.embeddings_df = None
    
    def save_embeddings(self, videos_with_embeddings: List[Dict]) -> bool:
        """
        Lưu embeddings vào file
        
        Args:
            videos_with_embeddings: List videos có embeddings
            
        Returns:
            True nếu thành công
        """
        try:
            import os
            
            # Tạo thư mục nếu chưa có
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            
            # Chuyển sang DataFrame
            df_data = []
            for video in videos_with_embeddings:
                row = {
                    'video_id': video['video_id'],
                    'title': video['title'],
                    'description': video.get('description', ''),
                    'channel_name': video.get('channel_name', ''),
                    'channel_id': video.get('channel_id', ''),
                    'video_url': video['video_url'],
                    'published_date': video.get('published_date'),
                    'view_count': video.get('view_count', 0),
                    'like_count': video.get('like_count', 0),
                    'duration': video.get('duration', 0),
                    'thumbnail_url': video.get('thumbnail_url', ''),
                    'summary': video.get('summary', ''),
                    'full_text': video.get('full_text', ''),
                    'embedding': video['embedding'],
                    'created_at': datetime.now()
                }
                df_data.append(row)
            
            df = pd.DataFrame(df_data)
            
            # Lưu bằng pickle (hỗ trợ numpy arrays)
            with open(self.storage_path, 'wb') as f:
                pickle.dump(df, f)
            
            logger.info(f"Saved {len(df)} embeddings to {self.storage_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving embeddings: {e}")
            return False
    
    def load_embeddings(self) -> Optional[pd.DataFrame]:
        """
        Load embeddings từ file
        
        Returns:
            DataFrame chứa embeddings
        """
        try:
            with open(self.storage_path, 'rb') as f:
                df = pickle.load(f)
            
            self.embeddings_df = df
            logger.info(f"Loaded {len(df)} embeddings from {self.storage_path}")
            return df
            
        except FileNotFoundError:
            logger.warning(f"Embeddings file not found: {self.storage_path}")
            return None
        except Exception as e:
            logger.error(f"Error loading embeddings: {e}")
            return None
    
    def get_all_videos(self) -> List[Dict]:
        """
        Lấy tất cả videos với embeddings
        
        Returns:
            List of video dictionaries
        """
        if self.embeddings_df is None:
            self.load_embeddings()
        
        if self.embeddings_df is None:
            return []
        
        return self.embeddings_df.to_dict('records')
    
    def get_video_by_id(self, video_id: str) -> Optional[Dict]:
        """
        Lấy một video theo ID
        
        Args:
            video_id: Video ID
            
        Returns:
            Video dictionary
        """
        if self.embeddings_df is None:
            self.load_embeddings()
        
        if self.embeddings_df is None:
            return None
        
        result = self.embeddings_df[self.embeddings_df['video_id'] == video_id]
        
        if len(result) == 0:
            return None
        
        return result.iloc[0].to_dict()
    
    def update_video(self, video_id: str, updates: Dict) -> bool:
        """
        Update thông tin video
        
        Args:
            video_id: Video ID
            updates: Dictionary chứa các field cần update
            
        Returns:
            True nếu thành công
        """
        if self.embeddings_df is None:
            self.load_embeddings()
        
        if self.embeddings_df is None:
            return False
        
        try:
            idx = self.embeddings_df[self.embeddings_df['video_id'] == video_id].index
            
            if len(idx) == 0:
                logger.warning(f"Video not found: {video_id}")
                return False
            
            for key, value in updates.items():
                self.embeddings_df.at[idx[0], key] = value
            
            # Save lại
            return self.save_embeddings(self.embeddings_df.to_dict('records'))
            
        except Exception as e:
            logger.error(f"Error updating video: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """
        Lấy thống kê về embeddings database
        
        Returns:
            Dictionary chứa stats
        """
        if self.embeddings_df is None:
            self.load_embeddings()
        
        if self.embeddings_df is None:
            return {}
        
        df = self.embeddings_df
        
        stats = {
            'total_videos': len(df),
            'total_channels': df['channel_name'].nunique(),
            'avg_views': df['view_count'].mean(),
            'median_views': df['view_count'].median(),
            'avg_duration': df['duration'].mean() / 60,  # minutes
            'date_range': {
                'oldest': df['published_date'].min(),
                'newest': df['published_date'].max()
            },
            'top_channels': df['channel_name'].value_counts().head(10).to_dict()
        }
        
        return stats
    
    def export_to_parquet(self, output_path='data/embeddings/videos_embeddings.parquet') -> bool:
        """
        Export sang parquet format (hiệu năng tốt hơn cho production)
        
        Args:
            output_path: Đường dẫn output
            
        Returns:
            True nếu thành công
        """
        if self.embeddings_df is None:
            self.load_embeddings()
        
        if self.embeddings_df is None:
            return False
        
        try:
            import os
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Convert embeddings sang format phù hợp với parquet
            df = self.embeddings_df.copy()
            
            # Convert numpy array sang list để lưu parquet
            df['embedding'] = df['embedding'].apply(lambda x: x.tolist() if isinstance(x, np.ndarray) else x)
            
            df.to_parquet(output_path, engine='pyarrow', compression='snappy')
            
            logger.info(f"Exported to parquet: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting to parquet: {e}")
            return False