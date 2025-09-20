#!/usr/bin/env python3
"""
데이터베이스 초기화 스크립트
SET.sql 파일을 읽어서 데이터베이스에 테이블과 데이터를 생성합니다.
"""
import sqlite3
import os

def init_database():
    """Initialize database with SET.sql"""

    # Check if SET.sql exists
    if not os.path.exists("SET.sql"):
        print("❌ SET.sql 파일을 찾을 수 없습니다.")
        return False

    try:
        # Read SET.sql file
        with open("SET.sql", "r", encoding="utf-8") as f:
            sql_content = f.read()

        # Connect to database
        conn = sqlite3.connect("BurgeriaDB.db")
        cursor = conn.cursor()

        # Execute SQL script
        cursor.executescript(sql_content)
        conn.commit()
        conn.close()

        print("✅ 데이터베이스 초기화 완료!")

        # Verify data
        conn = sqlite3.connect("BurgeriaDB.db")
        cursor = conn.cursor()

        # Check Set_Items count
        cursor.execute("SELECT COUNT(*) FROM Set_Items")
        set_items_count = cursor.fetchone()[0]

        # Check Products count
        cursor.execute("SELECT COUNT(*) FROM Products")
        products_count = cursor.fetchone()[0]

        conn.close()

        print(f"📊 Products 테이블: {products_count}개 상품")
        print(f"📊 Set_Items 테이블: {set_items_count}개 세트 구성품")

        return True

    except Exception as e:
        print(f"❌ 데이터베이스 초기화 실패: {str(e)}")
        return False

if __name__ == "__main__":
    print("=== Burgeria 데이터베이스 초기화 ===")
    if init_database():
        print("\n이제 order_bot.py를 실행할 수 있습니다!")
    else:
        print("\n초기화에 실패했습니다. SET.sql 파일을 확인해주세요.")