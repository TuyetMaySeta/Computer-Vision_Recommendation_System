import os
from dotenv import load_dotenv

load_dotenv()

# YouTube API Settings
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'

# OpenAI API Settings
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_EMBEDDING_MODEL = os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')
OPENAI_EMBEDDING_DIMENSION = 1536

# Database Settings
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'youtube_videos_db'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}

# Embeddings Storage Settings
EMBEDDINGS_STORAGE_PATH = os.getenv('EMBEDDINGS_STORAGE_PATH', 'data/embeddings/videos_embeddings.pkl')
EMBEDDINGS_PARQUET_PATH = os.getenv('EMBEDDINGS_PARQUET_PATH', 'data/embeddings/videos_embeddings.parquet')

# Thêm vào cuối file config/settings.py
# Embedding Settings
USE_LOCAL_EMBEDDINGS = os.getenv('USE_LOCAL_EMBEDDINGS', 'true').lower() == 'true'
LOCAL_EMBEDDING_MODEL = os.getenv('LOCAL_EMBEDDING_MODEL', 'all-MiniLM-L6-v2')

# Collection Settings
MAX_RESULTS_PER_QUERY = int(os.getenv('MAX_RESULTS_PER_QUERY', 50))
MAX_VIDEOS_PER_KEYWORD = int(os.getenv('MAX_VIDEOS_PER_KEYWORD', 100))
MAX_VIDEOS_PER_CHANNEL = int(os.getenv('MAX_VIDEOS_PER_CHANNEL', 200))

# API Rate Limiting
API_QUOTA_LIMIT = int(os.getenv('API_QUOTA_LIMIT', 10000))
SLEEP_BETWEEN_REQUESTS = float(os.getenv('SLEEP_BETWEEN_REQUESTS', 1))

# Input Processing Settings
MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', 50))
MAX_PDF_PAGES = int(os.getenv('MAX_PDF_PAGES', 100))

# Similarity & Ranking Settings
SIMILARITY_WEIGHT = float(os.getenv('SIMILARITY_WEIGHT', 0.70))
POPULARITY_WEIGHT = float(os.getenv('POPULARITY_WEIGHT', 0.15))
RECENCY_WEIGHT = float(os.getenv('RECENCY_WEIGHT', 0.10))
CHANNEL_WEIGHT = float(os.getenv('CHANNEL_WEIGHT', 0.05))

MIN_VIEW_COUNT = int(os.getenv('MIN_VIEW_COUNT', 1000))
MAX_VIDEO_AGE_YEARS = int(os.getenv('MAX_VIDEO_AGE_YEARS', 5))
MIN_VIDEO_DURATION = int(os.getenv('MIN_VIDEO_DURATION', 120))  # seconds
MAX_VIDEO_DURATION = int(os.getenv('MAX_VIDEO_DURATION', 10800))  # seconds
MAX_VIDEOS_PER_CHANNEL_RESULT = int(os.getenv('MAX_VIDEOS_PER_CHANNEL_RESULT', 2))

# Logging Settings
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'data/logs/system.log')

# Keywords for AI/ML content
DEFAULT_KEYWORDS = [
    "machine learning tutorial",
    "deep learning explained",
    "data science course",
    "neural networks tutorial",
    "AI fundamentals",
    "artificial intelligence course",
    "python machine learning",
    "tensorflow tutorial",
    "pytorch tutorial",
    "computer vision tutorial",
    "natural language processing",
    "reinforcement learning",
    "transformer architecture",
    "deep learning from scratch",
    "machine learning algorithms"
]

# Quality channels for AI/ML content
QUALITY_CHANNELS = [
    "Yannic Kilcher",
    "Two Minute Papers",
    "Sentdex",
    "StatQuest with Josh Starmer",
    "3Blue1Brown",
    "Lex Fridman",
    "Andrew Ng",
    "deeplizard",
    "CodeEmporium",
    "Arxiv Insights",
    "Stanford Online",
    "MIT OpenCourseWare",
    "DeepLearningAI",
    "Weights & Biases"
]