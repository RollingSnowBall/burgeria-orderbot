"""
Database repository classes
"""
import sqlite3
import json
from typing import List, Optional, Dict, Any
from models.product import Product, SetComponent
from models.cart import CartItem
from models.order import OrderItem
from .connection import DatabaseConnection


class ProductRepository:
    # 제품 데이터 접근 계층 (데이터베이스 CRUD 작업)

    def __init__(self, db_connection: DatabaseConnection):
        # DatabaseConnection 인스턴스 주입
        self.db = db_connection

    def find_products(self, category: Optional[str] = None) -> List[Product]:
        # 카테고리별로 제품 검색 (재고 있는 상품만)
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # 기본 SQL 쿼리 (재고 있는 상품만 조회)
            sql = """
            SELECT product_id, product_name, product_type, price, description, stock_quantity
            FROM Products
            WHERE stock_quantity > 0
            """
            params = []

            # 카테고리 필터 추가
            if category:
                sql += " AND product_type = ?"
                params.append(category)

            cursor.execute(sql, params)
            products = []

            for row in cursor.fetchall():
                products.append(Product(
                    product_id=row[0],
                    product_name=row[1],
                    product_type=row[2],
                    price=row[3],
                    description=row[4],
                    stock_quantity=row[5]
                ))

            return products

    def get_product_by_id(self, product_id: str) -> Optional[Product]:
        # 제품 ID로 특정 제품 상세 정보 조회
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
            SELECT product_id, product_name, product_type, price, description, stock_quantity
            FROM Products WHERE product_id = ?
            """, (product_id,))

            result = cursor.fetchone()
            if result:
                return Product(
                    product_id=result[0],
                    product_name=result[1],
                    product_type=result[2],
                    price=result[3],
                    description=result[4],
                    stock_quantity=result[5]
                )
            return None

    def get_set_components(self, set_product_id: str) -> List[SetComponent]:
        # 세트 상품의 구성품들 조회 (버거, 사이드, 음료 등)
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # Set_Items와 Products 테이블을 조인하여 구성품 정보 가져오기
            cursor.execute("""
            SELECT si.component_product_id, p.product_name, p.product_type, p.price, si.quantity, si.is_default
            FROM Set_Items si
            JOIN Products p ON si.component_product_id = p.product_id
            WHERE si.set_product_id = ?
            """, (set_product_id,))

            components = []
            for row in cursor.fetchall():
                components.append(SetComponent(
                    product_id=row[0],
                    product_name=row[1],
                    product_type=row[2],
                    price=row[3],
                    quantity=row[4],
                    is_default=bool(row[5])
                ))

            return components

    def get_changeable_options(self, component_type: str) -> List[Product]:
        # 구성품 변경 시 선택 가능한 옵션들 조회 (사이드/음료)
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # 해당 타입의 상품들을 가격 순으로 조회
            cursor.execute("""
            SELECT product_id, product_name, price, description
            FROM Products
            WHERE product_type = ? AND stock_quantity > 0
            ORDER BY price ASC
            """, (component_type,))

            options = []
            for row in cursor.fetchall():
                options.append(Product(
                    product_id=row[0],
                    product_name=row[1],
                    product_type=component_type,
                    price=row[2],
                    description=row[3]
                ))

            return options


class CartRepository:
    # 장바구니 데이터 접근 계층 (세션별 장바구니 관리)

    def __init__(self, db_connection: DatabaseConnection):
        # DatabaseConnection 인스턴스 주입
        self.db = db_connection

    def add_item(self, cart_item: CartItem, session_id: str) -> bool:
        # 장바구니에 상품 추가
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            try:
                # Cart 테이블에 새 아이템 삽입
                cursor.execute("""
                INSERT INTO Cart (
                    cart_item_id, session_id, product_id, product_name, order_type,
                    quantity, base_price, modifications, line_total, special_requests, set_group_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    cart_item.cart_item_id, session_id, cart_item.product_id, cart_item.product_name,
                    cart_item.order_type, cart_item.quantity, cart_item.base_price,
                    json.dumps([mod.__dict__ for mod in cart_item.modifications]),  # 변경사항을 JSON으로 직렬화
                    cart_item.line_total, cart_item.special_requests, cart_item.set_group_id
                ))

                conn.commit()
                return True
            except Exception:
                return False

    def get_cart_items(self, session_id: str) -> List[CartItem]:
        # 세션의 장바구니 아이템들 조회
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # 세션 ID로 장바구니 아이템들 조회 (생성순 정렬)
            cursor.execute("""
            SELECT cart_item_id, product_id, product_name, order_type, quantity, base_price,
                   modifications, line_total, special_requests, set_group_id
            FROM Cart WHERE session_id = ?
            ORDER BY created_at
            """, (session_id,))

            cart_items = []
            for row in cursor.fetchall():
                # JSON으로 저장된 변경사항들을 디시리얼라이즈
                modifications = json.loads(row[6]) if row[6] else []

                cart_items.append(CartItem(
                    cart_item_id=row[0],
                    product_id=row[1],
                    product_name=row[2],
                    order_type=row[3],
                    quantity=row[4],
                    base_price=row[5],
                    modifications=modifications,
                    line_total=row[7],
                    special_requests=row[8],
                    set_group_id=row[9]
                ))

            return cart_items

    def clear_cart(self, session_id: str, cart_item_id: Optional[str] = None) -> Dict[str, Any]:
        # 장바구니 아이템 삭제 (전체 또는 특정 아이템)
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            try:
                if cart_item_id:
                    # 특정 아이템만 삭제
                    cursor.execute("DELETE FROM Cart WHERE cart_item_id = ? AND session_id = ?",
                                 (cart_item_id, session_id))
                    removed_items = cursor.rowcount
                else:
                    # 전체 장바구니 비우기
                    cursor.execute("SELECT COUNT(*) FROM Cart WHERE session_id = ?", (session_id,))
                    removed_items = cursor.fetchone()[0]
                    cursor.execute("DELETE FROM Cart WHERE session_id = ?", (session_id,))

                cursor.execute("SELECT COUNT(*) FROM Cart WHERE session_id = ?", (session_id,))
                remaining_items = cursor.fetchone()[0]

                conn.commit()

                return {
                    "success": True,
                    "removed_items": removed_items,
                    "remaining_items": remaining_items
                }

            except Exception as e:
                return {
                    "success": False,
                    "error": str(e)
                }

    def update_cart_item(self, session_id: str, cart_item_id: str, new_quantity: int) -> bool:
        # 장바구니 아이템의 수량 업데이트
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            try:
                # 현재 아이템 정보 가져오기 (가격 재계산을 위해)
                cursor.execute("""
                SELECT base_price, modifications
                FROM Cart WHERE cart_item_id = ? AND session_id = ?
                """, (cart_item_id, session_id))

                result = cursor.fetchone()
                if not result:
                    return False

                # 변경사항 비용을 포함한 새로운 총액 계산
                base_price, mods_json = result
                modifications = json.loads(mods_json) if mods_json else []
                modification_cost = sum(mod.get("price_change", 0) for mod in modifications)
                new_line_total = (base_price + modification_cost) * new_quantity

                cursor.execute("""
                UPDATE Cart SET quantity = ?, line_total = ?
                WHERE cart_item_id = ? AND session_id = ?
                """, (new_quantity, new_line_total, cart_item_id, session_id))

                conn.commit()
                return True

            except Exception:
                return False


class OrderRepository:
    # 주문 데이터 접근 계층 (주문 생성 및 조회)

    def __init__(self, db_connection: DatabaseConnection):
        # DatabaseConnection 인스턴스 주입
        self.db = db_connection

    def create_order(self, order_id: str, session_id: str, total_amount: int,
                    order_type: str, customer_name: str, customer_phone: str,
                    estimated_time: int) -> bool:
        # 새로운 주문 생성
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            try:
                # Orders 테이블에 주문 정보 삽입
                cursor.execute("""
                INSERT INTO Orders (
                    order_id, session_id, total_amount, order_type,
                    customer_name, customer_phone, estimated_time, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    order_id, session_id, total_amount, order_type,
                    customer_name, customer_phone, estimated_time, "confirmed"  # 초기 상태는 확인됨
                ))

                conn.commit()
                return True

            except Exception:
                return False

    def add_order_item(self, order_item: OrderItem) -> bool:
        # 주문에 아이템 추가
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            try:
                # Order_Items 테이블에 주문 아이템 삽입
                cursor.execute("""
                INSERT INTO Order_Items (
                    order_item_id, order_id, product_id, product_name, order_type,
                    quantity, base_price, modifications, line_total, special_requests, set_group_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    order_item.order_item_id, order_item.order_id, order_item.product_id,
                    order_item.product_name, order_item.order_type,
                    order_item.quantity, order_item.base_price,
                    json.dumps([mod.__dict__ for mod in order_item.modifications]),  # 변경사항을 JSON으로 직렬화
                    order_item.line_total, order_item.special_requests, order_item.set_group_id
                ))

                conn.commit()
                return True

            except Exception:
                return False

    def get_order_details(self, order_id: str) -> Optional[Dict[str, Any]]:
        # 주문 상세 정보 조회 (주문정보 + 주문아이템들)
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # 먼저 주문 기본 정보 가져오기
            cursor.execute("""
            SELECT order_id, session_id, total_amount, order_type, customer_name,
                   customer_phone, status, estimated_time, created_at
            FROM Orders WHERE order_id = ?
            """, (order_id,))

            order_row = cursor.fetchone()
            if not order_row:
                return None

            # 해당 주문의 아이템들 가져오기
            cursor.execute("""
            SELECT order_item_id, product_id, product_name, order_type, quantity,
                   base_price, modifications, line_total, special_requests, set_group_id
            FROM Order_Items WHERE order_id = ?
            ORDER BY set_group_id, order_item_id
            """, (order_id,))

            order_items = []
            for item_row in cursor.fetchall():
                # JSON으로 저장된 변경사항들을 디시리얼라이즈
                modifications = json.loads(item_row[6]) if item_row[6] else []

                order_items.append({
                    "order_item_id": item_row[0],
                    "product_id": item_row[1],
                    "product_name": item_row[2],
                    "order_type": item_row[3],
                    "quantity": item_row[4],
                    "base_price": item_row[5],
                    "modifications": modifications,
                    "line_total": item_row[7],
                    "special_requests": item_row[8],
                    "set_group_id": item_row[9]
                })

            return {
                "order_info": {
                    "order_id": order_row[0],
                    "session_id": order_row[1],
                    "total_amount": order_row[2],
                    "order_type": order_row[3],
                    "customer_name": order_row[4],
                    "customer_phone": order_row[5],
                    "status": order_row[6],
                    "estimated_time": order_row[7],
                    "created_at": order_row[8]
                },
                "order_items": order_items
            }