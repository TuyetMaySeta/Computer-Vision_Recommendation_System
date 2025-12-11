import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from config.settings import DB_CONFIG
from utils.logger import get_logger

logger = get_logger(__name__)

class DatabaseConnection:
    _connection_pool = None
    
    @classmethod
    def initialize_pool(cls, minconn=1, maxconn=10):
        """Khởi tạo connection pool"""
        try:
            cls._connection_pool = pool.SimpleConnectionPool(
                minconn,
                maxconn,
                **DB_CONFIG
            )
            logger.info("Database connection pool initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing connection pool: {e}")
            raise
    
    @classmethod
    def get_connection(cls):
        """Lấy connection từ pool"""
        if cls._connection_pool is None:
            cls.initialize_pool()
        return cls._connection_pool.getconn()
    
    @classmethod
    def return_connection(cls, connection):
        """Trả connection về pool"""
        if cls._connection_pool:
            cls._connection_pool.putconn(connection)
    
    @classmethod
    def close_all_connections(cls):
        """Đóng tất cả connections"""
        if cls._connection_pool:
            cls._connection_pool.closeall()
            logger.info("All database connections closed")

def get_db_connection():
    """Helper function để lấy connection"""
    return DatabaseConnection.get_connection()

def execute_query(query, params=None, fetch=False):
    """
    Thực thi query
    
    Args:
        query: SQL query
        params: Query parameters
        fetch: True nếu muốn fetch results
    
    Returns:
        Results nếu fetch=True, None nếu không
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(query, params)
        
        if fetch:
            results = cursor.fetchall()
            return results
        else:
            conn.commit()
            return cursor.rowcount
            
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            DatabaseConnection.return_connection(conn)

def execute_many(query, data_list):
    """
    Thực thi nhiều queries cùng lúc (bulk insert)
    
    Args:
        query: SQL query
        data_list: List of tuples containing data
    
    Returns:
        Number of rows affected
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.executemany(query, data_list)
        conn.commit()
        
        return cursor.rowcount
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error in execute_many: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            DatabaseConnection.return_connection(conn)