#!/usr/bin/env python3
"""
Main script để tìm kiếm video dựa trên text query, image và/hoặc file
UPDATED: Hỗ trợ xử lý ảnh với OCR
"""

import sys
import os
import argparse
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from processors.image_processor import MultimodalProcessor
from processors.similarity import SimilarityCalculator
from database.embeddings_store import EmbeddingsStore
from processors.embeddings import EmbeddingGenerator
from utils.logger import get_logger

logger = get_logger(__name__)

def search_videos(query_text=None, image_path=None, file_path=None, top_k=5):
    """
    Tìm kiếm video dựa trên query, image và/hoặc file
    
    Args:
        query_text: Text query từ user
        image_path: Đường dẫn file ảnh (JPG, PNG, etc.)
        file_path: Đường dẫn file PDF/Word
        top_k: Số lượng kết quả trả về
        
    Returns:
        List of recommended videos
    """
    logger.info("=" * 60)
    logger.info("YOUTUBE VIDEO RECOMMENDATION SYSTEM (MULTIMODAL)")
    logger.info("=" * 60)
    
    # Validate input
    if not query_text and not image_path and not file_path:
        logger.error("Must provide at least one input: query_text, image_path, or file_path")
        return None
    
    # 1. Xử lý multimodal input
    logger.info("\n[Step 1/4] Processing multimodal input...")
    
    if image_path:
        logger.info(f"   📷 Image: {image_path}")
    if file_path:
        logger.info(f"   📄 Document: {file_path}")
    if query_text:
        logger.info(f"   💬 Query: {query_text}")
    
    multimodal_processor = MultimodalProcessor()
    
    processed_text = multimodal_processor.process_multimodal_input(
        text_query=query_text,
        image_path=image_path,
        pdf_path=file_path
    )
    
    if not processed_text:
        logger.error("Failed to process input")
        return None
    
    logger.info(f"✅ Processed input: {len(processed_text)} characters")
    
    # 2. Tạo embedding cho query
    logger.info("\n[Step 2/4] Creating query embedding...")
    embedding_generator = EmbeddingGenerator()
    
    query_embedding = embedding_generator.create_embedding(processed_text)
    
    if query_embedding is None:
        logger.error("Failed to create query embedding")
        return None
    
    logger.info(f"✅ Query embedding created: shape {query_embedding.shape}")
    
    # 3. Load video embeddings database
    logger.info("\n[Step 3/4] Loading video database...")
    embeddings_store = EmbeddingsStore()
    
    videos = embeddings_store.get_all_videos()
    
    if not videos:
        logger.error("No videos in database. Please run data collection first.")
        return None
    
    logger.info(f"✅ Loaded {len(videos)} videos from database")
    
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
        query_text or "multimodal query"
    )
    
    return formatted_results

def display_results(results):
    """Hiển thị kết quả với metrics"""
    import numpy as np
    
    print("\n" + "=" * 100)
    print("🎥 TOP RECOMMENDED VIDEOS")
    print("=" * 100)
    
    for video in results:
        print(f"\n{video['rank']}. {video['title']}")
        print(f"   👤 {video['channel']} | 👁️  {video['view_count']} views | ⏱️  {video['duration']}")
        print(f"   📅 {video['published_date']} | 🎯 Similarity: {video['similarity_score']:.3f} | ⭐ Final: {video['final_score']:.3f}")
        print(f"   🔗 {video['url']}")
        print(f"   📝 {video['why_relevant']}")
        print(f"   💡 {video['summary'][:120]}...")
    
    # Metrics
    print("\n" + "=" * 100)
    print("📊 RECOMMENDATION METRICS")
    print("=" * 100)
    
    similarity_scores = [v['similarity_score'] for v in results]
    
    print(f"\n🎯 Similarity Analysis:")
    print(f"   Mean:       {np.mean(similarity_scores):.4f}")
    print(f"   Median:     {np.median(similarity_scores):.4f}")
    print(f"   Range:      [{np.min(similarity_scores):.4f}, {np.max(similarity_scores):.4f}]")
    
    high_sim = sum(1 for s in similarity_scores if s >= 0.7)
    med_sim = sum(1 for s in similarity_scores if 0.5 <= s < 0.7)
    low_sim = sum(1 for s in similarity_scores if s < 0.5)
    
    print(f"\n   Distribution:")
    print(f"   ├─ High (≥0.7):      {high_sim}/{len(results)} ({high_sim/len(results)*100:.1f}%)")
    print(f"   ├─ Medium (0.5-0.7): {med_sim}/{len(results)} ({med_sim/len(results)*100:.1f}%)")
    print(f"   └─ Low (<0.5):       {low_sim}/{len(results)} ({low_sim/len(results)*100:.1f}%)")
    
    channels = [v['channel'] for v in results]
    unique_channels = len(set(channels))
    
    print(f"\n🌈 Diversity:")
    print(f"   Unique Channels: {unique_channels}/{len(results)} ({unique_channels/len(results)*100:.0f}%)")
    
    quality = np.mean(similarity_scores) * 100
    print(f"\n🏆 Overall Quality Score: {quality:.1f}/100")
    
    print("\n" + "=" * 100)

def save_results(results, output_file='search_results.json'):
    """Lưu kết quả ra JSON"""
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
        description='Search YouTube videos using text, images, and/or documents'
    )
    
    parser.add_argument(
        '-q', '--query',
        type=str,
        help='Text query (e.g., "transformer architecture")'
    )
    
    parser.add_argument(
        '-i', '--image',
        type=str,
        help='Path to image file (JPG, PNG, etc.)'
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
    if not args.query and not args.image and not args.file:
        parser.error("Must provide at least one of: --query, --image, or --file")
    
    try:
        # Search videos
        results = search_videos(
            query_text=args.query,
            image_path=args.image,
            file_path=args.file,
            top_k=args.top_k
        )
        
        if not results:
            logger.error("Search failed")
            return 1
        
        # Display results
        display_results(results)
        
        # Save results
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