"""
Database connection management
"""
import sqlite3
from contextlib import contextmanager
from typing import Generator


class DatabaseConnection:
    """Database connection manager"""

    def __init__(self, db_path: str = "C:\\data\\BurgeriaDB.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize database connection and create tables if needed"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Create cart table for session management
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS Cart (
                cart_item_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                product_id TEXT NOT NULL,
                product_name TEXT NOT NULL,
                order_type TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                base_price INTEGER NOT NULL,
                modifications TEXT,
                line_total INTEGER NOT NULL,
                special_requests TEXT,
                set_group_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')

            # Create orders table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS Orders (
                order_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                total_amount INTEGER NOT NULL,
                order_type TEXT NOT NULL,
                customer_name TEXT,
                customer_phone TEXT,
                status TEXT DEFAULT 'pending',
                estimated_time INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')

            # Create order items table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS Order_Items (
                order_item_id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                product_id TEXT NOT NULL,
                product_name TEXT NOT NULL,
                order_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                base_price INTEGER NOT NULL,
                modifications TEXT,
                line_total INTEGER NOT NULL,
                special_requests TEXT,
                set_group_id TEXT,
                FOREIGN KEY(order_id) REFERENCES Orders(order_id)
            )
            ''')

            conn.commit()

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get database connection with context manager"""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()