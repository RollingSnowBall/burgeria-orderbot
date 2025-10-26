"""
Task 1.2: findProduct 함수 (SQL LIKE 기반 정확한 이름 검색 버전)
Task 1.3: addToCart 함수 (단품 버전)
Task 2.1: getSetComposition 함수 (세트 구성품 조회)
Task 3.1: findProduct 함수 (시맨틱 검색 업그레이드)
Task 3.3: 장바구니 관리 함수 3종 (getCartDetails, updateCartItem, clearCart)
Task 4.1: processOrder 함수 (주문 생성)

Phase 1 MVP를 위한 기본 검색 및 장바구니 추가 기능
Phase 2 세트 메뉴 및 옵션 처리 기능
Phase 3 검색 고도화 및 사용자 경험 개선 (장바구니 관리 포함)
Phase 4 주문 완료 및 시스템 안정화
"""

import sqlite3
import uuid
import platform
import os
import json
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional, List
from openai import OpenAI
from dotenv import load_dotenv

# 환경변수 로드 (OpenAI API 키)
load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


def get_default_db_path() -> str:
    """운영체제에 따라 기본 DB 경로 반환"""
    if platform.system() == "Windows":
        return "C:\\data\\BurgeriaDB.db"
    else:  # macOS, Linux
        # Mac의 경우 현재 프로젝트 디렉토리의 data 폴더 사용
        return os.path.expanduser("/Users/juno/Desktop/claude/Burgeria/BurgeriaDB.db")


def _get_embedding(text: str, model: str = "text-embedding-3-small") -> Optional[List[float]]:
    """텍스트의 임베딩 벡터 생성"""
    try:
        response = client.embeddings.create(
            input=text,
            model=model
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"임베딩 생성 오류: {e}")
        return None


def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """두 벡터 간의 코사인 유사도 계산"""
    vec1_np = np.array(vec1)
    vec2_np = np.array(vec2)
    dot_product = np.dot(vec1_np, vec2_np)
    norm_vec1 = np.linalg.norm(vec1_np)
    norm_vec2 = np.linalg.norm(vec2_np)

    if norm_vec1 == 0 or norm_vec2 == 0:
        return 0.0

    return dot_product / (norm_vec1 * norm_vec2)


def findProduct(
    query: str,
    category: Optional[str] = None,
    limit: int = 5,
    db_path: str = None,
    similarity_threshold: float = 0.50,
    ambiguity_threshold: float = 0.08
) -> Dict[str, Any]:
    """
    임베딩 기반 시맨틱 검색을 사용한 상품 검색 (Task 3.1)

    Args:
        query: 검색할 메뉴명 (예: '한우불고기버거', '매콤한 감자')
        category: 카테고리 필터 (선택사항: 'burger', 'sides', 'beverage', 'set' 등)
        limit: 최대 반환 결과 수 (기본값: 5)
        db_path: 데이터베이스 경로
        similarity_threshold: 유사도 임계값 (이 값 이상만 매칭으로 간주)
        ambiguity_threshold: 모호성 임계값 (상위 결과들 간 유사도 차이가 이 값 이하면 AMBIGUOUS)

    Returns:
        {
            "success": bool,
            "status": "FOUND" | "AMBIGUOUS" | "NOT_FOUND" | "ERROR",
            "product": {...} or None,  # FOUND일 때만
            "matches": [...],           # AMBIGUOUS일 때 여러 후보 반환
            "total_found": int,
            "message": str
        }

    Examples:
        >>> findProduct("한우불고기버거")
        {"status": "FOUND", "product": {...}, ...}

        >>> findProduct("양념감자")
        {"status": "AMBIGUOUS", "matches": [4개의 양념감자 옵션], ...}

        >>> findProduct("매콤한 감자")
        {"status": "FOUND", "product": {"product_name": "양념감자 (칠리)", ...}, ...}
    """
    if db_path is None:
        db_path = get_default_db_path()

    try:
        # 1. 쿼리의 임베딩 생성
        query_embedding = _get_embedding(query)

        if query_embedding is None:
            return {
                "success": False,
                "status": "ERROR",
                "product": None,
                "matches": [],
                "total_found": 0,
                "message": "임베딩 생성에 실패했습니다."
            }

        # 2. DB에서 모든 상품과 임베딩 조회
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        sql = """
        SELECT product_id, product_name, product_type, price, description,
               stock_quantity, category_id, embedding
        FROM Products
        WHERE stock_quantity > 0 AND embedding IS NOT NULL
        """
        params = []

        # 카테고리 필터 추가
        if category:
            sql += " AND product_type = ?"
            params.append(category)

        cursor.execute(sql, params)
        all_products = cursor.fetchall()
        conn.close()

        if not all_products:
            return {
                "success": True,
                "status": "NOT_FOUND",
                "product": None,
                "matches": [],
                "total_found": 0,
                "message": f"'{query}' 상품을 찾을 수 없습니다."
            }

        # 3. 각 상품과의 유사도 계산
        similarities = []
        for product in all_products:
            product_embedding = json.loads(product[7])  # embedding 컬럼
            similarity = _cosine_similarity(query_embedding, product_embedding)

            if similarity >= similarity_threshold:
                similarities.append({
                    "product_id": product[0],
                    "product_name": product[1],
                    "product_type": product[2],
                    "price": product[3],
                    "description": product[4],
                    "stock_quantity": product[5],
                    "category_id": product[6],
                    "match_score": round(similarity, 4)
                })

        # 4. 유사도 내림차순 정렬
        similarities.sort(key=lambda x: x["match_score"], reverse=True)

        # 5. 상위 limit개만 선택
        top_matches = similarities[:limit]

        if not top_matches:
            return {
                "success": True,
                "status": "NOT_FOUND",
                "product": None,
                "matches": [],
                "total_found": 0,
                "message": f"'{query}'와 유사한 상품을 찾을 수 없습니다."
            }

        # 6. 모호성 판단
        # 상위 2개 이상의 결과가 있고, 점수 차이가 작으면 AMBIGUOUS
        if len(top_matches) >= 2:
            score_diff = top_matches[0]["match_score"] - top_matches[1]["match_score"]

            if score_diff <= ambiguity_threshold:
                return {
                    "success": True,
                    "status": "AMBIGUOUS",
                    "product": None,
                    "matches": top_matches,
                    "total_found": len(similarities),
                    "message": f"'{query}'와 유사한 상품이 {len(top_matches)}개 있습니다. 구체적으로 말씀해주세요."
                }

        # 7. 명확한 1개 결과 (FOUND)
        best_match = top_matches[0]

        return {
            "success": True,
            "status": "FOUND",
            "product": best_match,
            "matches": top_matches,
            "total_found": len(similarities),
            "message": f"'{best_match['product_name']}' 상품을 찾았습니다."
        }

    except Exception as e:
        return {
            "success": False,
            "status": "ERROR",
            "product": None,
            "matches": [],
            "total_found": 0,
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
    단품 또는 세트 메뉴를 장바구니에 추가 (Task 1.3 + Task 2.2)

    Args:
        session_id: 사용자 세션 ID
        product_id: 상품 ID (예: 'A00001' 단품, 'G00001' 세트)
        quantity: 주문 수량 (기본값: 1)
        special_requests: 특별 요청사항 (기본값: "")
        db_path: 데이터베이스 경로

    Returns:
        {
            "success": bool,
            "cart_item_id": str or None (세트의 경우 리스트),
            "product_name": str,
            "quantity": int,
            "line_total": int,
            "message": str,
            "set_group_id": str or None (세트 메뉴인 경우)
        }

    Examples:
        # 단품
        >>> addToCart("session_123", "A00001", quantity=1)
        {"success": True, "cart_item_id": "CART_XXX", "product_name": "한우불고기버거", ...}

        # 세트
        >>> addToCart("session_123", "G00001", quantity=1)
        {"success": True, "set_group_id": "SET_XXX", "product_name": "한우불고기버거 세트", ...}
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

        # 2. 재고 확인
        if stock <= 0:
            conn.close()
            return {
                "success": False,
                "cart_item_id": None,
                "message": f"'{prod_name}'는 품절되었습니다."
            }

        # 3. 세트 메뉴 처리 (Task 2.2)
        if prod_type == 'set':
            return _addSetToCart(
                cursor, conn, session_id, prod_id, prod_name, price,
                quantity, special_requests, db_path
            )

        # 4. 단품 메뉴 처리 (Task 1.3)
        cart_item_id = f"CART_{uuid.uuid4().hex[:8].upper()}"
        order_type = "single"
        base_price = price
        line_total = price * quantity
        modifications = ""

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
        if 'conn' in locals():
            conn.close()
        return {
            "success": False,
            "cart_item_id": None,
            "message": f"장바구니 추가 중 오류 발생: {str(e)}"
        }


def _addSetToCart(
    cursor, conn, session_id: str, set_product_id: str,
    set_name: str, set_price: int, quantity: int,
    special_requests: str, db_path: str
) -> Dict[str, Any]:
    """
    세트 메뉴를 장바구니에 추가하는 내부 함수 (Task 2.2)

    세트의 모든 구성품을 동일한 set_group_id로 묶어서 Cart에 추가
    """
    try:
        # 1. 세트 구성품 조회
        set_composition = getSetComposition(set_product_id, db_path)

        if not set_composition['success']:
            conn.close()
            return {
                "success": False,
                "cart_item_id": None,
                "message": set_composition['message']
            }

        components = set_composition['items']

        if not components:
            conn.close()
            return {
                "success": False,
                "cart_item_id": None,
                "message": f"'{set_name}' 세트의 구성품이 없습니다."
            }

        # 2. 세트 그룹 ID 생성
        set_group_id = f"SET_{uuid.uuid4().hex[:8].upper()}"

        # 3. 각 구성품을 Cart에 추가
        cart_item_ids = []
        total_component_price = 0

        for component in components:
            cart_item_id = f"CART_{uuid.uuid4().hex[:8].upper()}"
            comp_quantity = component['quantity'] * quantity  # 세트 수량 반영
            comp_price = component['price']
            comp_line_total = comp_price * comp_quantity

            total_component_price += comp_price * component['quantity']

            cursor.execute("""
            INSERT INTO Cart (
                cart_item_id, session_id, product_id, product_name, order_type,
                quantity, base_price, modifications, line_total, special_requests, set_group_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cart_item_id, session_id, component['product_id'], component['product_name'],
                "set", comp_quantity, comp_price, "", comp_line_total, special_requests, set_group_id
            ))

            cart_item_ids.append(cart_item_id)

        conn.commit()
        conn.close()

        # 4. 세트 총액 계산
        set_total = set_price * quantity

        return {
            "success": True,
            "cart_item_ids": cart_item_ids,
            "set_group_id": set_group_id,
            "product_id": set_product_id,
            "product_name": set_name,
            "quantity": quantity,
            "base_price": set_price,
            "line_total": set_total,
            "components_count": len(components),
            "message": f"'{set_name}' {quantity}개를 장바구니에 담았습니다. (구성품 {len(components)}개)"
        }

    except Exception as e:
        conn.close()
        return {
            "success": False,
            "cart_item_id": None,
            "message": f"세트 메뉴 장바구니 추가 중 오류 발생: {str(e)}"
        }


def getSetComposition(set_product_id: str, db_path: str = None) -> Dict[str, Any]:
    """
    세트 메뉴의 기본 구성품 목록을 조회 (Task 2.1)

    Args:
        set_product_id: 세트 상품 ID (예: 'G00001')
        db_path: 데이터베이스 경로

    Returns:
        {
            "success": bool,
            "set_product_id": str,
            "set_name": str or None,
            "items": [
                {
                    "product_id": str,
                    "product_name": str,
                    "category_id": str,
                    "product_type": str,
                    "price": int,
                    "quantity": int
                },
                ...
            ],
            "message": str
        }

    Examples:
        >>> getSetComposition("G00001")
        {
            "success": True,
            "set_product_id": "G00001",
            "set_name": "한우불고기버거 세트",
            "items": [
                {"product_id": "A00001", "product_name": "한우불고기버거", ...},
                {"product_id": "B00001", "product_name": "포테이토 (미디움)", ...},
                {"product_id": "C00001", "product_name": "콜라 (미디움)", ...}
            ],
            "message": "세트 구성품 3개를 조회했습니다."
        }
    """
    if db_path is None:
        db_path = get_default_db_path()

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 1. 세트 상품 정보 확인
        cursor.execute("""
        SELECT product_name, product_type
        FROM Products
        WHERE product_id = ?
        """, (set_product_id,))

        set_info = cursor.fetchone()

        if not set_info:
            conn.close()
            return {
                "success": False,
                "set_product_id": set_product_id,
                "set_name": None,
                "items": [],
                "message": f"세트 상품 ID '{set_product_id}'를 찾을 수 없습니다."
            }

        set_name, product_type = set_info

        # 2. 세트 메뉴인지 확인
        if product_type != 'set':
            conn.close()
            return {
                "success": False,
                "set_product_id": set_product_id,
                "set_name": set_name,
                "items": [],
                "message": f"'{set_name}'는 세트 메뉴가 아닙니다. (타입: {product_type})"
            }

        # 3. 세트 구성품 조회 (Set_Items + Products JOIN)
        cursor.execute("""
        SELECT
            p.product_id,
            p.product_name,
            p.category_id,
            p.product_type,
            p.price,
            si.quantity
        FROM Set_Items si
        JOIN Products p ON si.component_product_id = p.product_id
        WHERE si.set_product_id = ? AND si.is_default = 1
        ORDER BY p.product_type
        """, (set_product_id,))

        components = cursor.fetchall()
        conn.close()

        if not components:
            return {
                "success": False,
                "set_product_id": set_product_id,
                "set_name": set_name,
                "items": [],
                "message": f"'{set_name}' 세트의 구성품 정보가 없습니다."
            }

        # 4. 구성품 리스트 구성
        items = []
        for comp in components:
            items.append({
                "product_id": comp[0],
                "product_name": comp[1],
                "category_id": comp[2],
                "product_type": comp[3],
                "price": comp[4],
                "quantity": comp[5]
            })

        return {
            "success": True,
            "set_product_id": set_product_id,
            "set_name": set_name,
            "items": items,
            "message": f"세트 구성품 {len(items)}개를 조회했습니다."
        }

    except Exception as e:
        return {
            "success": False,
            "set_product_id": set_product_id,
            "set_name": None,
            "items": [],
            "message": f"세트 구성품 조회 중 오류 발생: {str(e)}"
        }


def getCartDetails(session_id: str, db_path: str = None) -> Dict[str, Any]:
    """
    장바구니 전체 조회 (Task 3.3)

    Args:
        session_id: 사용자 세션 ID
        db_path: 데이터베이스 경로

    Returns:
        {
            "success": bool,
            "session_id": str,
            "items": [
                {
                    "cart_item_id": str,
                    "product_id": str,
                    "product_name": str,
                    "order_type": str,  # "single" or "set"
                    "quantity": int,
                    "base_price": int,
                    "line_total": int,
                    "special_requests": str,
                    "set_group_id": str or None,
                    "created_at": str
                },
                ...
            ],
            "total_items": int,
            "total_price": int,
            "message": str
        }

    Examples:
        >>> getCartDetails("session_123")
        {
            "success": True,
            "session_id": "session_123",
            "items": [...],
            "total_items": 3,
            "total_price": 10200,
            "message": "장바구니에 3개의 상품이 있습니다."
        }
    """
    if db_path is None:
        db_path = get_default_db_path()

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 장바구니 조회
        cursor.execute("""
        SELECT
            cart_item_id, product_id, product_name, order_type,
            quantity, base_price, line_total, special_requests,
            set_group_id, created_at
        FROM Cart
        WHERE session_id = ?
        ORDER BY created_at ASC
        """, (session_id,))

        cart_rows = cursor.fetchall()
        conn.close()

        if not cart_rows:
            return {
                "success": True,
                "session_id": session_id,
                "items": [],
                "total_items": 0,
                "total_price": 0,
                "message": "장바구니가 비어 있습니다."
            }

        # 장바구니 항목 구성
        items = []
        total_price = 0

        for row in cart_rows:
            item = {
                "cart_item_id": row[0],
                "product_id": row[1],
                "product_name": row[2],
                "order_type": row[3],
                "quantity": row[4],
                "base_price": row[5],
                "line_total": row[6],
                "special_requests": row[7] if row[7] else "",
                "set_group_id": row[8],
                "created_at": row[9]
            }
            items.append(item)
            total_price += row[6]  # line_total

        return {
            "success": True,
            "session_id": session_id,
            "items": items,
            "total_items": len(items),
            "total_price": total_price,
            "message": f"장바구니에 {len(items)}개의 상품이 있습니다."
        }

    except Exception as e:
        return {
            "success": False,
            "session_id": session_id,
            "items": [],
            "total_items": 0,
            "total_price": 0,
            "message": f"장바구니 조회 중 오류 발생: {str(e)}"
        }


def updateCartItem(cart_item_id: str, quantity: int, db_path: str = None) -> Dict[str, Any]:
    """
    장바구니 항목의 수량 변경 (Task 3.3)

    Args:
        cart_item_id: 장바구니 항목 ID
        quantity: 변경할 수량 (0이면 삭제)
        db_path: 데이터베이스 경로

    Returns:
        {
            "success": bool,
            "cart_item_id": str,
            "product_name": str or None,
            "old_quantity": int,
            "new_quantity": int,
            "new_line_total": int or None,
            "message": str
        }

    Examples:
        >>> updateCartItem("CART_ABC123", 2)
        {
            "success": True,
            "cart_item_id": "CART_ABC123",
            "product_name": "한우불고기버거",
            "old_quantity": 1,
            "new_quantity": 2,
            "new_line_total": 14000,
            "message": "'한우불고기버거' 수량이 1개에서 2개로 변경되었습니다."
        }

        >>> updateCartItem("CART_ABC123", 0)
        {
            "success": True,
            "cart_item_id": "CART_ABC123",
            "product_name": "한우불고기버거",
            "old_quantity": 1,
            "new_quantity": 0,
            "message": "'한우불고기버거'가 장바구니에서 삭제되었습니다."
        }
    """
    if db_path is None:
        db_path = get_default_db_path()

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 1. 기존 장바구니 항목 조회
        cursor.execute("""
        SELECT product_name, quantity, base_price
        FROM Cart
        WHERE cart_item_id = ?
        """, (cart_item_id,))

        cart_item = cursor.fetchone()

        if not cart_item:
            conn.close()
            return {
                "success": False,
                "cart_item_id": cart_item_id,
                "product_name": None,
                "old_quantity": 0,
                "new_quantity": 0,
                "new_line_total": None,
                "message": f"장바구니 항목 ID '{cart_item_id}'를 찾을 수 없습니다."
            }

        product_name = cart_item[0]
        old_quantity = cart_item[1]
        base_price = cart_item[2]

        # 2. 수량이 0이면 삭제
        if quantity == 0:
            cursor.execute("DELETE FROM Cart WHERE cart_item_id = ?", (cart_item_id,))
            conn.commit()
            conn.close()

            return {
                "success": True,
                "cart_item_id": cart_item_id,
                "product_name": product_name,
                "old_quantity": old_quantity,
                "new_quantity": 0,
                "new_line_total": None,
                "message": f"'{product_name}'가 장바구니에서 삭제되었습니다."
            }

        # 3. 수량 변경
        new_line_total = base_price * quantity

        cursor.execute("""
        UPDATE Cart
        SET quantity = ?, line_total = ?
        WHERE cart_item_id = ?
        """, (quantity, new_line_total, cart_item_id))

        conn.commit()
        conn.close()

        return {
            "success": True,
            "cart_item_id": cart_item_id,
            "product_name": product_name,
            "old_quantity": old_quantity,
            "new_quantity": quantity,
            "new_line_total": new_line_total,
            "message": f"'{product_name}' 수량이 {old_quantity}개에서 {quantity}개로 변경되었습니다."
        }

    except Exception as e:
        if 'conn' in locals():
            conn.close()
        return {
            "success": False,
            "cart_item_id": cart_item_id,
            "product_name": None,
            "old_quantity": 0,
            "new_quantity": 0,
            "new_line_total": None,
            "message": f"수량 변경 중 오류 발생: {str(e)}"
        }


def clearCart(session_id: str, db_path: str = None) -> Dict[str, Any]:
    """
    장바구니 전체 비우기 (Task 3.3)

    Args:
        session_id: 사용자 세션 ID
        db_path: 데이터베이스 경로

    Returns:
        {
            "success": bool,
            "session_id": str,
            "deleted_count": int,
            "message": str
        }

    Examples:
        >>> clearCart("session_123")
        {
            "success": True,
            "session_id": "session_123",
            "deleted_count": 5,
            "message": "장바구니가 비워졌습니다. (5개 항목 삭제)"
        }
    """
    if db_path is None:
        db_path = get_default_db_path()

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 1. 삭제할 항목 수 확인
        cursor.execute("SELECT COUNT(*) FROM Cart WHERE session_id = ?", (session_id,))
        count = cursor.fetchone()[0]

        # 2. 장바구니 비우기
        cursor.execute("DELETE FROM Cart WHERE session_id = ?", (session_id,))

        conn.commit()
        conn.close()

        if count == 0:
            return {
                "success": True,
                "session_id": session_id,
                "deleted_count": 0,
                "message": "장바구니가 이미 비어 있습니다."
            }

        return {
            "success": True,
            "session_id": session_id,
            "deleted_count": count,
            "message": f"장바구니가 비워졌습니다. ({count}개 항목 삭제)"
        }

    except Exception as e:
        if 'conn' in locals():
            conn.close()
        return {
            "success": False,
            "session_id": session_id,
            "deleted_count": 0,
            "message": f"장바구니 비우기 중 오류 발생: {str(e)}"
        }


def getSetMenusInCart(
    session_id: str,
    set_product_id: str = None,
    db_path: str = None
) -> Dict[str, Any]:
    """
    장바구니에 있는 세트 메뉴 목록 조회 (Task 3.4 헬퍼 함수)

    Args:
        session_id: 사용자 세션 ID
        set_product_id: 특정 세트 상품 ID (선택사항, 예: 'G00001')
        db_path: 데이터베이스 경로

    Returns:
        {
            "success": bool,
            "sets": [
                {
                    "set_group_id": str,
                    "set_product_id": str,
                    "set_name": str,
                    "items": [
                        {
                            "cart_item_id": str,
                            "product_id": str,
                            "product_name": str,
                            "quantity": int,
                            "base_price": int
                        },
                        ...
                    ],
                    "total_price": int,
                    "created_at": str
                },
                ...
            ],
            "total_count": int,
            "message": str
        }

    Examples:
        >>> getSetMenusInCart("session_123")
        {
            "success": True,
            "sets": [
                {
                    "set_group_id": "SET_ABC123",
                    "set_name": "한우불고기버거 세트",
                    "items": [...],
                    "total_price": 13000
                }
            ],
            "total_count": 1
        }
    """
    if db_path is None:
        db_path = get_default_db_path()

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 1. 세트 그룹 ID 목록 조회
        sql = """
        SELECT DISTINCT set_group_id, MIN(created_at) as created_at
        FROM Cart
        WHERE session_id = ? AND set_group_id IS NOT NULL
        """
        params = [session_id]
        sql += " GROUP BY set_group_id ORDER BY created_at ASC"

        cursor.execute(sql, params)
        set_groups = cursor.fetchall()

        if not set_groups:
            conn.close()
            return {
                "success": True,
                "sets": [],
                "total_count": 0,
                "message": "장바구니에 세트 메뉴가 없습니다."
            }

        # 2. 각 세트의 상세 정보 조회
        sets = []
        for set_group_id, created_at in set_groups:
            # 세트 항목들 조회
            cursor.execute("""
            SELECT cart_item_id, product_id, product_name, quantity, base_price, line_total
            FROM Cart
            WHERE session_id = ? AND set_group_id = ?
            ORDER BY cart_item_id
            """, (session_id, set_group_id))

            items = []
            total_price = 0
            set_name = None
            found_set_product_id = None

            for row in cursor.fetchall():
                items.append({
                    "cart_item_id": row[0],
                    "product_id": row[1],
                    "product_name": row[2],
                    "quantity": row[3],
                    "base_price": row[4]
                })
                total_price += row[5]  # line_total

            # 세트 상품 ID 찾기: 모든 구성품이 일치하는 세트 찾기
            if items:
                # 현재 세트의 모든 product_id 수집
                cart_product_ids = set(item['product_id'] for item in items)

                # Set_Items에서 이 구성품들로 이루어진 세트 찾기
                cursor.execute("""
                SELECT DISTINCT p.product_id, p.product_name
                FROM Products p
                WHERE p.product_type = 'set'
                """)

                potential_sets = cursor.fetchall()

                best_match = None
                max_match_count = 0

                # 각 세트의 구성품과 비교하여 가장 일치하는 세트 찾기
                for potential_set_id, potential_set_name in potential_sets:
                    cursor.execute("""
                    SELECT component_product_id
                    FROM Set_Items
                    WHERE set_product_id = ? AND is_default = TRUE
                    """, (potential_set_id,))

                    default_components = set(row[0] for row in cursor.fetchall())

                    # 구성품 개수가 다르면 건너뛰기
                    if len(default_components) != len(cart_product_ids):
                        continue

                    # 일치하는 구성품 개수 계산
                    match_count = len(cart_product_ids.intersection(default_components))

                    # 더 많이 일치하는 세트로 업데이트
                    if match_count > max_match_count:
                        max_match_count = match_count
                        best_match = (potential_set_id, potential_set_name)

                # 가장 잘 일치하는 세트 선택
                if best_match:
                    found_set_product_id, set_name = best_match
                else:
                    set_name = "세트 메뉴"

            # set_product_id 필터링 (지정된 경우)
            if set_product_id and found_set_product_id != set_product_id:
                # 필터 조건에 맞지 않으면 건너뛰기
                continue

            sets.append({
                "set_group_id": set_group_id,
                "set_product_id": found_set_product_id,
                "set_name": set_name,
                "items": items,
                "total_price": total_price,
                "created_at": created_at
            })

        conn.close()

        return {
            "success": True,
            "sets": sets,
            "total_count": len(sets),
            "message": f"장바구니에 {len(sets)}개의 세트 메뉴가 있습니다."
        }

    except Exception as e:
        if 'conn' in locals():
            conn.close()
        return {
            "success": False,
            "sets": [],
            "total_count": 0,
            "message": f"세트 메뉴 조회 중 오류 발생: {str(e)}"
        }


def updateSetItem(
    session_id: str,
    old_product_id: str,
    new_product_id: str,
    set_group_id: str = None,
    db_path: str = None
) -> Dict[str, Any]:
    """
    세트 메뉴의 구성품을 교체 (Task 3.4)

    - set_group_id가 제공된 경우: 해당 세트의 구성품을 직접 교체
    - set_group_id가 없고 1개 세트만 있는 경우: 자동으로 해당 세트 교체
    - set_group_id가 없고 여러 세트가 있는 경우: "MULTIPLE_SETS" 상태 반환 (선택 필요)

    Args:
        session_id: 사용자 세션 ID
        old_product_id: 교체할 기존 상품 ID
        new_product_id: 새로 추가할 상품 ID
        set_group_id: 특정 세트 그룹 ID (선택사항)
        db_path: 데이터베이스 경로

    Returns:
        성공 시:
        {
            "status": "UPDATED",
            "success": True,
            "set_group_id": str,
            "old_product": {"id": str, "name": str, "price": int},
            "new_product": {"id": str, "name": str, "price": int},
            "price_difference": int,
            "message": str
        }

        여러 세트 중 선택 필요 시:
        {
            "status": "MULTIPLE_SETS",
            "success": False,
            "sets": [{"set_group_id": str, "set_name": str, "items": [...], ...}],
            "message": str
        }

        실패 시:
        {
            "status": "ERROR",
            "success": False,
            "message": str
        }

    Examples:
        >>> # 자동 선택 (1개 세트만 있는 경우)
        >>> updateSetItem("session_123", "B00001", "B00002")
        {
            "status": "UPDATED",
            "success": True,
            "set_group_id": "SET_ABC123",
            "old_product": {"id": "B00001", "name": "포테이토", "price": 2000},
            "new_product": {"id": "B00002", "name": "양념감자 (칠리)", "price": 2600},
            "price_difference": 600,
            "message": "포테이토를 양념감자 (칠리)로 교체했습니다. (추가 600원)"
        }

        >>> # 수동 선택 필요 (여러 세트)
        >>> updateSetItem("session_123", "B00001", "B00002")
        {
            "status": "MULTIPLE_SETS",
            "success": False,
            "sets": [...],
            "message": "여러 세트 메뉴가 있습니다. 어떤 세트를 변경하시겠습니까?"
        }
    """
    if db_path is None:
        db_path = get_default_db_path()

    conn = None

    try:
        # 1. 교체 대상 세트 찾기
        if set_group_id:
            # set_group_id가 제공된 경우: 해당 세트만 조회
            sets_result = getSetMenusInCart(session_id, db_path=db_path)
            if not sets_result['success']:
                return {
                    "status": "ERROR",
                    "success": False,
                    "message": sets_result['message']
                }

            # 특정 set_group_id를 가진 세트 찾기
            target_set = None
            for s in sets_result['sets']:
                if s['set_group_id'] == set_group_id:
                    target_set = s
                    break

            if not target_set:
                return {
                    "status": "ERROR",
                    "success": False,
                    "message": f"세트 그룹 ID '{set_group_id}'를 찾을 수 없습니다."
                }

            # old_product_id가 이 세트에 포함되어 있는지 확인
            has_old_product = any(item['product_id'] == old_product_id for item in target_set['items'])
            if not has_old_product:
                return {
                    "status": "ERROR",
                    "success": False,
                    "message": f"세트에 '{old_product_id}' 상품이 포함되어 있지 않습니다."
                }

            matching_sets = [target_set]

        else:
            # set_group_id가 없는 경우: old_product_id를 포함한 모든 세트 찾기
            sets_result = getSetMenusInCart(session_id, db_path=db_path)
            if not sets_result['success']:
                return {
                    "status": "ERROR",
                    "success": False,
                    "message": sets_result['message']
                }

            # old_product_id를 포함한 세트만 필터링
            matching_sets = []
            for s in sets_result['sets']:
                has_old_product = any(item['product_id'] == old_product_id for item in s['items'])
                if has_old_product:
                    matching_sets.append(s)

            if len(matching_sets) == 0:
                return {
                    "status": "ERROR",
                    "success": False,
                    "message": f"'{old_product_id}' 상품이 포함된 세트 메뉴가 없습니다."
                }

            if len(matching_sets) > 1:
                # 여러 세트가 있는 경우: 사용자 선택 필요
                return {
                    "status": "MULTIPLE_SETS",
                    "success": False,
                    "sets": matching_sets,
                    "message": f"{len(matching_sets)}개의 세트 메뉴가 있습니다. 어떤 세트를 변경하시겠습니까?"
                }

        # 2. 단일 세트 자동 선택 또는 지정된 세트 교체
        target_set = matching_sets[0]
        target_set_group_id = target_set['set_group_id']

        # 3. 새 상품 정보 조회
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
        SELECT product_id, product_name, price, category_id
        FROM Products
        WHERE product_id = ?
        """, (new_product_id,))

        new_product_row = cursor.fetchone()
        if not new_product_row:
            conn.close()
            return {
                "status": "ERROR",
                "success": False,
                "message": f"새 상품 '{new_product_id}'를 찾을 수 없습니다."
            }

        new_product_info = {
            "id": new_product_row[0],
            "name": new_product_row[1],
            "price": new_product_row[2],
            "category_id": new_product_row[3]
        }

        # 4. 기존 상품 정보 조회
        cursor.execute("""
        SELECT product_id, product_name, price, category_id
        FROM Products
        WHERE product_id = ?
        """, (old_product_id,))

        old_product_row = cursor.fetchone()
        if not old_product_row:
            conn.close()
            return {
                "status": "ERROR",
                "success": False,
                "message": f"기존 상품 '{old_product_id}'를 찾을 수 없습니다."
            }

        old_product_info = {
            "id": old_product_row[0],
            "name": old_product_row[1],
            "price": old_product_row[2],
            "category_id": old_product_row[3]
        }

        # 5. 카테고리 일치 확인 (선택사항이지만 권장)
        if old_product_info['category_id'] != new_product_info['category_id']:
            # 경고는 하되, 교체는 허용
            pass

        # 6. 가격 차이 계산
        price_difference = new_product_info['price'] - old_product_info['price']

        # 7. Cart 테이블에서 기존 상품을 새 상품으로 교체
        cursor.execute("""
        UPDATE Cart
        SET
            product_id = ?,
            product_name = ?,
            base_price = ?,
            line_total = ? * quantity
        WHERE session_id = ?
          AND set_group_id = ?
          AND product_id = ?
        """, (
            new_product_info['id'],
            new_product_info['name'],
            new_product_info['price'],
            new_product_info['price'],
            session_id,
            target_set_group_id,
            old_product_info['id']
        ))

        rows_updated = cursor.rowcount

        if rows_updated == 0:
            conn.close()
            return {
                "status": "ERROR",
                "success": False,
                "message": "장바구니 업데이트 실패. 해당 상품을 찾을 수 없습니다."
            }

        conn.commit()
        conn.close()

        # 8. 성공 메시지 생성
        if price_difference > 0:
            price_msg = f" (추가 {price_difference:,}원)"
        elif price_difference < 0:
            price_msg = f" (할인 {abs(price_difference):,}원)"
        else:
            price_msg = ""

        return {
            "status": "UPDATED",
            "success": True,
            "set_group_id": target_set_group_id,
            "old_product": {
                "id": old_product_info['id'],
                "name": old_product_info['name'],
                "price": old_product_info['price']
            },
            "new_product": {
                "id": new_product_info['id'],
                "name": new_product_info['name'],
                "price": new_product_info['price']
            },
            "price_difference": price_difference,
            "message": f"{old_product_info['name']}를 {new_product_info['name']}로 교체했습니다.{price_msg}"
        }

    except Exception as e:
        if conn:
            conn.close()
        return {
            "status": "ERROR",
            "success": False,
            "message": f"세트 상품 교체 중 오류 발생: {str(e)}"
        }


def processOrder(
    session_id: str,
    customer_name: str = "",
    customer_phone: str = "",
    order_type: str = "takeout",
    db_path: str = None
) -> Dict[str, Any]:
    """
    장바구니 내용을 기반으로 주문 생성 (Task 4.1)

    Args:
        session_id: 사용자 세션 ID
        customer_name: 고객 이름 (선택사항)
        customer_phone: 고객 전화번호 (선택사항)
        order_type: 주문 유형 ("takeout", "delivery", "dine-in") 기본값: "takeout"
        db_path: 데이터베이스 경로

    Returns:
        {
            "success": bool,
            "order_id": str,
            "order_number": int,
            "total_items": int,
            "total_price": int,
            "created_at": str,
            "message": str
        }

    Examples:
        >>> processOrder("session_123", customer_name="홍길동", customer_phone="010-1234-5678")
        {
            "success": True,
            "order_id": "ORD_ABC12345",
            "order_number": 1,
            "total_items": 3,
            "total_price": 20000,
            "created_at": "2025-10-26 15:30:00",
            "message": "주문이 완료되었습니다. 주문번호: 1"
        }
    """
    if db_path is None:
        db_path = get_default_db_path()

    try:
        # 1. 장바구니 조회
        cart = getCartDetails(session_id, db_path)

        if not cart['success']:
            return {
                "success": False,
                "order_id": None,
                "order_number": None,
                "total_items": 0,
                "total_price": 0,
                "created_at": None,
                "message": f"장바구니 조회 실패: {cart['message']}"
            }

        if cart['total_items'] == 0:
            return {
                "success": False,
                "order_id": None,
                "order_number": None,
                "total_items": 0,
                "total_price": 0,
                "created_at": None,
                "message": "장바구니가 비어 있습니다. 상품을 먼저 담아주세요."
            }

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 2. 주문 ID 생성
        order_id = f"ORD_{uuid.uuid4().hex[:8].upper()}"

        # 3. 주문 번호 생성 (오늘의 주문 카운트 + 1)
        cursor.execute("""
        SELECT COUNT(*) FROM Orders
        WHERE DATE(created_at) = DATE('now')
        """)
        today_order_count = cursor.fetchone()[0]
        order_number = today_order_count + 1

        # 4. Orders 테이블에 주문 생성
        cursor.execute("""
        INSERT INTO Orders (
            order_id, session_id, total_amount, order_type,
            customer_name, customer_phone, status, estimated_time
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_id,
            session_id,
            cart['total_price'],
            order_type,
            customer_name if customer_name else "",
            customer_phone if customer_phone else "",
            "pending",
            15  # 예상 소요 시간 15분
        ))

        # 5. Order_Items 테이블에 주문 항목들 저장
        for item in cart['items']:
            order_item_id = f"OITEM_{uuid.uuid4().hex[:8].upper()}"

            cursor.execute("""
            INSERT INTO Order_Items (
                order_item_id, order_id, product_id, product_name, order_type,
                quantity, base_price, modifications, line_total,
                special_requests, set_group_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_item_id,
                order_id,
                item['product_id'],
                item['product_name'],
                item['order_type'],
                item['quantity'],
                item['base_price'],
                "",  # modifications
                item['line_total'],
                item['special_requests'],
                item['set_group_id']
            ))

        # 6. 주문 생성 시간 조회
        cursor.execute("SELECT created_at FROM Orders WHERE order_id = ?", (order_id,))
        created_at = cursor.fetchone()[0]

        # 7. 장바구니 비우기
        cursor.execute("DELETE FROM Cart WHERE session_id = ?", (session_id,))

        conn.commit()
        conn.close()

        return {
            "success": True,
            "order_id": order_id,
            "order_number": order_number,
            "total_items": cart['total_items'],
            "total_price": cart['total_price'],
            "created_at": created_at,
            "message": f"주문이 완료되었습니다. 주문번호: {order_number}"
        }

    except Exception as e:
        if 'conn' in locals():
            conn.close()
        return {
            "success": False,
            "order_id": None,
            "order_number": None,
            "total_items": 0,
            "total_price": 0,
            "created_at": None,
            "message": f"주문 처리 중 오류 발생: {str(e)}"
        }
