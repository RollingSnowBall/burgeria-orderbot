"""
Database connection management
"""
import sqlite3
from contextlib import contextmanager
from typing import Generator


class DatabaseConnection:
    # 데이터베이스 연결을 관리하는 클래스

    def __init__(self, db_path: str = "C:\\data\\BurgeriaDB.db"):
        # 데이터베이스 파일 경로 설정 및 초기화
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        # 데이터베이스 연결 초기화 및 필요한 테이블 생성
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 세션 관리를 위한 장바구니 테이블 생성
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

            # 주문 정보를 저장하는 테이블 생성
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

            # 주문 아이템 상세 정보를 저장하는 테이블 생성
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
        # 컨텍스트 매니저를 사용하여 데이터베이스 연결 자동 관리
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()