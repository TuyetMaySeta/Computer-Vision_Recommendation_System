#!/usr/bin/env python3
"""
Script để khởi tạo database
"""

import sys
import os

# Thêm thư mục gốc vào Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.models import init_database
from database.connection import DatabaseConnection
from utils.logger import get_logger

logger = get_logger(__name__)

def main():
    """Khởi tạo database"""
    logger.info("=" * 60)
    logger.info("Starting database initialization...")
    logger.info("=" * 60)
    
    try:
        # Khởi tạo connection pool
        DatabaseConnection.initialize_pool()
        
        # Tạo tables
        success = init_database()
        
        if success:
            logger.info("=" * 60)
            logger.info("Database initialization completed successfully!")
            logger.info("=" * 60)
            return 0
        else:
            logger.error("Database initialization failed!")
            return 1
            
    except Exception as e:
        logger.error(f"Fatal error during initialization: {e}")
        return 1
    finally:
        DatabaseConnection.close_all_connections()

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)