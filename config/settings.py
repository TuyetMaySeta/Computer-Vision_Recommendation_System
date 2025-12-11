import os
from dotenv import load_dotenv

load_dotenv()

# YouTube API Settings
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'

# Database Settings
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'youtube_videos_db'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}

# Collection Settings
MAX_RESULTS_PER_QUERY = int(os.getenv('MAX_RESULTS_PER_QUERY', 50))
MAX_VIDEOS_PER_KEYWORD = int(os.getenv('MAX_VIDEOS_PER_KEYWORD', 100))
MAX_VIDEOS_PER_CHANNEL = int(os.getenv('MAX_VIDEOS_PER_CHANNEL', 200))

# API Rate Limiting
API_QUOTA_LIMIT = int(os.getenv('API_QUOTA_LIMIT', 10000))
SLEEP_BETWEEN_REQUESTS = float(os.getenv('SLEEP_BETWEEN_REQUESTS', 1))

# Logging Settings
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'data/logs/collector.log')

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
    "computer vision tutorial"
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
    "Arxiv Insights"
]