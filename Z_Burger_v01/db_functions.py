"""
Task 1.2: findProduct 함수 (SQL LIKE 기반 정확한 이름 검색 버전)
Task 1.3: addToCart 함수 (단품 버전)
Phase 1 MVP를 위한 기본 검색 및 장바구니 추가 기능
"""

import sqlite3
import uuid
import platform
import os
from datetime import datetime
from typing import Dict, Any, Optional


def get_default_db_path() -> str:
    """운영체제에 따라 기본 DB 경로 반환"""
    if platform.system() == "Windows":
        return "C:\\data\\BurgeriaDB.db"
    else:  # macOS, Linux
        # Mac의 경우 현재 프로젝트 디렉토리의 data 폴더 사용
        return os.path.expanduser("/Users/juno/Desktop/claude/Burgeria/BurgeriaDB.db")


def findProduct(query: str, category: Optional[str] = None, db_path: str = None) -> Dict[str, Any]:
    """
    사용자 입력과 정확히 일치하거나 포함하는 상품을 검색 (SQL LIKE 사용)

    Args:
        query: 검색할 메뉴명 (예: '한우불고기버거')
        category: 카테고리 필터 (선택사항: 'burger', 'sides', 'beverage', 'set' 등)
        db_path: 데이터베이스 경로

    Returns:
        {
            "success": bool,
            "status": "FOUND" | "NOT_FOUND" | "ERROR",
            "product": {...} or None,
            "message": str
        }

    Examples:
        >>> findProduct("한우불고기버거")
        {"success": True, "status": "FOUND", "product": {...}, "message": "..."}

        >>> findProduct("없는메뉴")
        {"success": True, "status": "NOT_FOUND", "product": None, "message": "..."}
    """
    if db_path is None:
        db_path = get_default_db_path()

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # SQL 쿼리: product_name이 query를 포함하는 경우
        sql = """
        SELECT product_id, product_name, product_type, price, description, stock_quantity
        FROM Products
        WHERE product_name LIKE ? AND stock_quantity > 0
        """
        params = [f"%{query}%"]

        # 카테고리 필터 추가
        if category:
            sql += " AND product_type = ?"
            params.append(category)

        cursor.execute(sql, params)
        result = cursor.fetchone()

        conn.close()

        if result:
            product_data = {
                "product_id": result[0],
                "product_name": result[1],
                "product_type": result[2],
                "price": result[3],
                "description": result[4],
                "stock_quantity": result[5]
            }

            return {
                "success": True,
                "status": "FOUND",
                "product": product_data,
                "message": f"'{result[1]}' 상품을 찾았습니다."
            }
        else:
            return {
                "success": True,
                "status": "NOT_FOUND",
                "product": None,
                "message": f"'{query}' 상품을 찾을 수 없습니다."
            }

    except Exception as e:
        return {
            "success": False,
            "status": "ERROR",
            "product": None,
            "message": f"검색 중 오류 발생: {str(e)}"
        }


def addToCart(
    session_id: str,
    product_id: str,
    quantity: int = 1,
    special_requests: str = "",
    db_path: str = None
) -> Dict[str, Any]:
    """
    단품 메뉴를 장바구니에 추가 (product_type != 'set')

    Args:
        session_id: 사용자 세션 ID
        product_id: 상품 ID (예: 'A00001')
        quantity: 주문 수량 (기본값: 1)
        special_requests: 특별 요청사항 (기본값: "")
        db_path: 데이터베이스 경로

    Returns:
        {
            "success": bool,
            "cart_item_id": str or None,
            "product_name": str,
            "quantity": int,
            "line_total": int,
            "message": str
        }

    Examples:
        >>> addToCart("session_123", "A00001", quantity=1)
        {"success": True, "cart_item_id": "...", "product_name": "한우불고기버거", ...}
    """
    if db_path is None:
        db_path = get_default_db_path()

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 1. 상품 정보 조회
        cursor.execute("""
        SELECT product_id, product_name, product_type, price, stock_quantity
        FROM Products
        WHERE product_id = ?
        """, (product_id,))

        product = cursor.fetchone()

        if not product:
            conn.close()
            return {
                "success": False,
                "cart_item_id": None,
                "message": f"상품 ID '{product_id}'를 찾을 수 없습니다."
            }

        prod_id, prod_name, prod_type, price, stock = product

        # 2. 세트 메뉴 체크 (단품만 허용)
        if prod_type == 'set':
            conn.close()
            return {
                "success": False,
                "cart_item_id": None,
                "message": f"'{prod_name}'는 세트 메뉴입니다. Task 2.2에서 구현 예정입니다."
            }

        # 3. 재고 확인
        if stock <= 0:
            conn.close()
            return {
                "success": False,
                "cart_item_id": None,
                "message": f"'{prod_name}'는 품절되었습니다."
            }

        # 4. 장바구니 아이템 생성
        cart_item_id = f"CART_{uuid.uuid4().hex[:8].upper()}"
        order_type = "single"
        base_price = price
        line_total = price * quantity
        modifications = ""  # 단품은 옵션 변경 없음

        # 5. Cart 테이블에 삽입
        cursor.execute("""
        INSERT INTO Cart (
            cart_item_id, session_id, product_id, product_name, order_type,
            quantity, base_price, modifications, line_total, special_requests, set_group_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cart_item_id, session_id, prod_id, prod_name, order_type,
            quantity, base_price, modifications, line_total, special_requests, None
        ))

        conn.commit()
        conn.close()

        return {
            "success": True,
            "cart_item_id": cart_item_id,
            "product_id": prod_id,
            "product_name": prod_name,
            "quantity": quantity,
            "base_price": base_price,
            "line_total": line_total,
            "message": f"'{prod_name}' {quantity}개를 장바구니에 담았습니다."
        }

    except Exception as e:
        return {
            "success": False,
            "cart_item_id": None,
            "message": f"장바구니 추가 중 오류 발생: {str(e)}"
        }
