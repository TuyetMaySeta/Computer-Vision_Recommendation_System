#!/usr/bin/env python3
"""
Flask web application cho YouTube Video Recommendation System
Serve cả frontend và backend API
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sys
import os
import tempfile

# Thêm thư mục gốc vào Python path
sys.path.insert(0, os.path.abspath('.'))

from processors.input_processor import InputProcessor
from processors.similarity import SimilarityCalculator
from database.embeddings_store import EmbeddingsStore
from processors.embeddings import EmbeddingGenerator
from utils.logger import get_logger

logger = get_logger(__name__)

# Initialize Flask app
app = Flask(__name__, static_folder='static')
CORS(app)

# Initialize components
embeddings_store = None
similarity_calc = None
embedding_generator = None
input_processor = None

def initialize_system():
    """Khởi tạo các components của hệ thống"""
    global embeddings_store, similarity_calc, embedding_generator, input_processor
    
    logger.info("Initializing recommendation system...")
    
    try:
        embeddings_store = EmbeddingsStore()
        similarity_calc = SimilarityCalculator()
        embedding_generator = EmbeddingGenerator()
        input_processor = InputProcessor()
        
        # Load videos database
        videos = embeddings_store.load_embeddings()
        
        if videos is None or len(videos) == 0:
            logger.warning("No videos in database! Please run data collection first.")
            return False
        
        logger.info(f"System initialized successfully! Loaded {len(videos)} videos.")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize system: {e}")
        return False

@app.route('/')
def index():
    """Serve trang chủ"""
    # Serve index.html từ thư mục hiện tại
    index_path = 'index.html'
    if os.path.exists(index_path):
        with open(index_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        return """
        <html>
        <head><title>Error</title></head>
        <body>
        <h1>Error: index.html not found!</h1>
        <p>Please create 'templates' folder and move index.html there, or place index.html in the root directory.</p>
        <pre>
Required structure:
Computer-Vision_Recommendation_System-main/
├── app.py
├── index.html  (hoặc)
└── templates/
    └── index.html
        </pre>
        </body>
        </html>
        """, 404

@app.route('/api/search', methods=['POST'])
def api_search():
    """
    API endpoint để search videos
    
    Expected form data:
        - query: text query (optional)
        - pdf: PDF file (optional)
        - top_k: number of results (default: 5)
    """
    try:
        # Get form data
        query = request.form.get('query', '').strip()
        top_k = int(request.form.get('top_k', 5))
        
        logger.info(f"Received search request: query='{query}', top_k={top_k}")
        
        # Validate input
        if not query and 'pdf' not in request.files:
            return jsonify({
                'error': 'Must provide at least one input: query or pdf'
            }), 400
        
        # Handle file upload
        pdf_path = None
        
        if 'pdf' in request.files and request.files['pdf'].filename:
            pdf_file = request.files['pdf']
            pdf_path = os.path.join(tempfile.gettempdir(), pdf_file.filename)
            pdf_file.save(pdf_path)
            logger.info(f"Saved PDF: {pdf_path}")
        
        # Process input
        logger.info("Processing input...")
        
        if pdf_path:
            # Extract PDF text
            raw_text, metadata = input_processor.extract_pdf_text(pdf_path)
            
            if not raw_text:
                # Clean up
                if pdf_path and os.path.exists(pdf_path):
                    os.remove(pdf_path)
                return jsonify({'error': 'Failed to extract text from PDF. Please ensure it is not a scanned image.'}), 400
            
            # Preprocess PDF text
            processed_pdf = input_processor.preprocess_file_text(raw_text, metadata)
            
            if query:
                # Combine query and PDF
                processed_query = input_processor.process_query_text(query)
                processed_text = input_processor.combine_query_and_file(
                    processed_query, 
                    processed_pdf, 
                    strategy='weighted'
                )
            else:
                # PDF only
                processed_text = processed_pdf
        else:
            # Query only
            processed_text = input_processor.process_query_text(query)
        
        if not processed_text:
            return jsonify({'error': 'Failed to process input'}), 500
        
        # Create query embedding
        logger.info("Creating query embedding...")
        query_embedding = embedding_generator.create_embedding(processed_text)
        
        if query_embedding is None:
            return jsonify({'error': 'Failed to create query embedding'}), 500
        
        # Load videos
        videos = embeddings_store.get_all_videos()
        
        if not videos:
            return jsonify({'error': 'No videos in database'}), 500
        
        # Rank videos
        logger.info("Ranking videos...")
        top_videos = similarity_calc.rank_videos(
            query_embedding=query_embedding,
            videos=videos,
            top_k=top_k
        )
        
        if not top_videos:
            return jsonify({'error': 'No matching videos found'}), 404
        
        # Format results
        formatted_results = similarity_calc.format_results(
            top_videos,
            query or "PDF document query"
        )
        
        logger.info(f"Returning {len(formatted_results)} results")
        
        # Clean up temporary files
        if pdf_path and os.path.exists(pdf_path):
            os.remove(pdf_path)
        
        return jsonify(formatted_results)
        
    except Exception as e:
        logger.error(f"Error in search: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def api_stats():
    """Get system statistics"""
    try:
        videos = embeddings_store.get_all_videos()
        stats = embeddings_store.get_stats()
        
        return jsonify({
            'total_videos': len(videos),
            'total_channels': stats.get('total_channels', 0),
            'avg_views': stats.get('avg_views', 0),
            'status': 'ready'
        })
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'system': 'YouTube Video Recommendation System',
        'version': '1.0'
    })

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🚀 YOUTUBE VIDEO RECOMMENDATION SYSTEM")
    print("=" * 60)
    
    # Initialize system
    if not initialize_system():
        print("\n❌ Failed to initialize system!")
        print("Please run the following first:")
        print("  1. python scripts/init_db.py")
        print("  2. python scripts/collect_by_keyword.py")
        print("  3. python scripts/build_embeddings.py")
        sys.exit(1)
    
    print("\n✅ System ready!")
    print("\n📍 Access the application at:")
    print("   🌐 http://localhost:5000")
    print("\n" + "=" * 60 + "\n")
    
    # Run Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)