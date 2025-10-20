"""
Task 1.2: findProduct 함수 (SQL LIKE 기반 정확한 이름 검색 버전)
Task 1.3: addToCart 함수 (단품 버전)
Task 2.1: getSetComposition 함수 (세트 구성품 조회)
Task 3.1: findProduct 함수 (시맨틱 검색 업그레이드)
Phase 1 MVP를 위한 기본 검색 및 장바구니 추가 기능
Phase 2 세트 메뉴 및 옵션 처리 기능
Phase 3 검색 고도화 및 사용자 경험 개선
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
