#!/usr/bin/env python3
"""
Main script để tìm kiếm video dựa trên text query và/hoặc file
"""

import sys
import os
import argparse
import json

# Thêm thư mục gốc vào Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from processors.input_processor import InputProcessor
from processors.similarity import SimilarityCalculator
from database.embeddings_store import EmbeddingsStore
from utils.logger import get_logger


# Chọn embedding generator dựa trên config
# Luôn dùng local embeddings (miễn phí)
from processors.embeddings import EmbeddingGenerator
logger = get_logger(__name__)

def search_videos(query_text=None, file_path=None, top_k=5):
    """
    Tìm kiếm video dựa trên query và/hoặc file
    
    Args:
        query_text: Text query từ user
        file_path: Đường dẫn file PDF/Word
        top_k: Số lượng kết quả trả về
        
    Returns:
        List of recommended videos
    """
    logger.info("=" * 60)
    logger.info("YOUTUBE VIDEO RECOMMENDATION SYSTEM")
    logger.info("=" * 60)
    
    # Validate input
    if not query_text and not file_path:
        logger.error("Must provide either query_text or file_path")
        return None
    
    # 1. Xử lý input
    logger.info("\n[Step 1/4] Processing input...")
    input_processor = InputProcessor()
    
    # Xác định file type
    file_type = None
    if file_path:
        if file_path.endswith('.pdf'):
            file_type = 'pdf'
        elif file_path.endswith('.docx') or file_path.endswith('.doc'):
            file_type = 'word'
        else:
            logger.error(f"Unsupported file type: {file_path}")
            return None
    
    processed_text = input_processor.process_input(
        query_text=query_text,
        file_path=file_path,
        file_type=file_type
    )
    
    if not processed_text:
        logger.error("Failed to process input")
        return None
    
    logger.info(f"Processed input: {len(processed_text)} characters")
    
    # 2. Tạo embedding cho query
    logger.info("\n[Step 2/4] Creating query embedding...")
    embedding_generator = EmbeddingGenerator()
    
    query_embedding = embedding_generator.create_embedding(processed_text)
    
    if query_embedding is None:
        logger.error("Failed to create query embedding")
        return None
    
    logger.info(f"Query embedding created: shape {query_embedding.shape}")
    
    # 3. Load video embeddings database
    logger.info("\n[Step 3/4] Loading video database...")
    embeddings_store = EmbeddingsStore()
    
    videos = embeddings_store.get_all_videos()
    
    if not videos:
        logger.error("No videos in database. Please run data collection first.")
        return None
    
    logger.info(f"Loaded {len(videos)} videos from database")
    
    # 4. Tính similarity và rank
    logger.info("\n[Step 4/4] Ranking videos...")
    similarity_calc = SimilarityCalculator()
    
    top_videos = similarity_calc.rank_videos(
        query_embedding=query_embedding,
        videos=videos,
        top_k=top_k
    )
    
    if not top_videos:
        logger.warning("No videos matched the criteria")
        return None
    
    # Format results
    formatted_results = similarity_calc.format_results(
        top_videos, 
        query_text or "uploaded document"
    )
    
    return formatted_results

def display_results(results):
    """
    Hiển thị kết quả tìm kiếm
    
    Args:
        results: List of recommended videos
    """
    print("\n" + "=" * 80)
    print("🎥 TOP RECOMMENDED VIDEOS")
    print("=" * 80)
    
    for video in results:
        print(f"\n{video['rank']}. {video['title']}")
        print(f"   👤 {video['channel']} | 👁️  {video['view_count']} views | ⏱️  {video['duration']}")
        print(f"   📅 {video['published_date']} | 🎯 Match: {video['similarity_score']:.1%}")
        print(f"   🔗 {video['url']}")
        print(f"   📝 {video['why_relevant']}")
        print(f"   💡 {video['summary'][:150]}...")
    
    print("\n" + "=" * 80)

def save_results(results, output_file='search_results.json'):
    """
    Lưu kết quả ra file JSON
    
    Args:
        results: List of recommended videos
        output_file: Output file path
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to: {output_file}")
        return True
    except Exception as e:
        logger.error(f"Error saving results: {e}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Search YouTube videos based on text query and/or document'
    )
    
    parser.add_argument(
        '-q', '--query',
        type=str,
        help='Text query (e.g., "transformer architecture")'
    )
    
    parser.add_argument(
        '-f', '--file',
        type=str,
        help='Path to PDF or Word file'
    )
    
    parser.add_argument(
        '-k', '--top-k',
        type=int,
        default=5,
        help='Number of results to return (default: 5)'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Output file path for JSON results'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.query and not args.file:
        parser.error("Must provide either --query or --file (or both)")
    
    try:
        # Search videos
        results = search_videos(
            query_text=args.query,
            file_path=args.file,
            top_k=args.top_k
        )
        
        if not results:
            logger.error("Search failed")
            return 1
        
        # Display results
        display_results(results)
        
        # Save results if output file specified
        if args.output:
            save_results(results, args.output)
        
        logger.info("\n✅ Search completed successfully!")
        return 0
        
    except KeyboardInterrupt:
        logger.info("\nSearch interrupted by user")
        return 1
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)