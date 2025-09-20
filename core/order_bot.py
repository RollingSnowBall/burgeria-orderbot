"""
Main BurgeriaOrderBot class - orchestrates all services
"""
from typing import Dict, List, Any, Optional
from difflib import SequenceMatcher

from database.connection import DatabaseConnection
from database.repository import ProductRepository, CartRepository, OrderRepository
from services.product_service import ProductService
from services.cart_service import CartService
from services.order_service import OrderService


class BurgeriaOrderBot:
    # 메인 주문 봇 클래스 - 모든 서비스를 조율하는 중앙 관리자

    def __init__(self, db_path: str = "C:\\\\data\\\\BurgeriaDB.db"):
        # 데이터베이스 연결 초기화
        self.db_connection = DatabaseConnection(db_path)

        # 리포지토리 레이어 초기화 (데이터 접근 계층)
        self.product_repo = ProductRepository(self.db_connection)
        self.cart_repo = CartRepository(self.db_connection)
        self.order_repo = OrderRepository(self.db_connection)

        # 서비스 레이어 초기화 (비즈니스 로직 계층)
        self.product_service = ProductService(self.product_repo)
        self.cart_service = CartService(self.cart_repo, self.product_service)
        self.order_service = OrderService(self.order_repo, self.cart_service)

    def similarity(self, a: str, b: str) -> float:
        # 두 문자열 간의 유사도 점수 계산 (0.0~1.0)
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    # === 제품 관련 메서드들 ===
    def find_product(self, query: str, category: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
        # 검색어와 일치하는 제품들을 찾아서 반환
        return self.product_service.find_product(query, category, limit)

    def get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        # 제품 ID로 특정 제품의 상세 정보 조회
        return self.product_service.get_product_by_id(product_id)

    def get_set_components(self, set_product_id: str) -> List[Dict[str, Any]]:
        # 세트 상품의 구성품 목록 조회 (버거, 사이드, 음료 등)
        return self.product_service.get_set_components(set_product_id)

    def get_changeable_options(self, component_type: str) -> List[Dict[str, Any]]:
        # 구성품 변경 시 선택 가능한 옵션들 조회
        return self.product_service.get_changeable_options(component_type)

    def get_set_change_options(self, set_product_id: str) -> Dict[str, Any]:
        # 세트 구성품과 변경 가능한 옵션들을 모두 조회
        return self.product_service.get_set_change_options(set_product_id)

    # === 장바구니 관련 메서드들 ===
    def add_to_cart(self, session_id: str, product_id: str, quantity: int = 1,
                   order_type: str = "single", modifications: List[Dict] = None,
                   special_requests: str = "") -> Dict[str, Any]:
        # 상품을 장바구니에 추가 (단품/세트, 옵션 변경 포함)
        return self.cart_service.add_to_cart(
            session_id, product_id, quantity, order_type, modifications, special_requests
        )

    def get_cart_details(self, session_id: str) -> Dict[str, Any]:
        # 세션의 현재 장바구니 내용과 총액 조회
        return self.cart_service.get_cart_details(session_id)

    def clear_cart(self, session_id: str, cart_item_id: Optional[str] = None,
                  clear_all: bool = False) -> Dict[str, Any]:
        # 장바구니 전체 비우기 또는 특정 상품만 제거
        return self.cart_service.clear_cart(session_id, cart_item_id, clear_all)

    def update_cart_item(self, session_id: str, cart_item_id: str,
                        new_quantity: Optional[int] = None,
                        modifications: Optional[List[Dict]] = None,
                        action: str = "update_quantity") -> Dict[str, Any]:
        # 장바구니 상품의 수량이나 옵션 수정
        return self.cart_service.update_cart_item(session_id, cart_item_id, new_quantity, action)

    # === 주문 관련 메서드들 ===
    def process_order(self, session_id: str, customer_info: Optional[Dict[str, str]] = None,
                     order_type: str = "takeout") -> Dict[str, Any]:
        # 장바구니 내용을 바탕으로 최종 주문 처리
        return self.order_service.process_order(session_id, customer_info, order_type)

    def get_order_details(self, order_id: str) -> Dict[str, Any]:
        # 특정 주문의 상세 정보 조회 (고객정보, 주문상품, 상태 등)
        return self.order_service.get_order_details(order_id)

    # === 하위 호환성을 위한 레거시 메서드들 ===
    def findProduct(self, query: str, category: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
        # 레거시 메서드명 - find_product로 리다이렉트
        return self.find_product(query, category, limit)

    def getSetChangeOptions(self, set_product_id: str) -> Dict[str, Any]:
        # 레거시 메서드명 - get_set_change_options로 리다이렉트
        return self.get_set_change_options(set_product_id)

    def addToCart(self, session_id: str, product_id: str, quantity: int = 1,
                  order_type: str = "single", modifications: List[Dict] = None,
                  special_requests: str = "") -> Dict[str, Any]:
        # 레거시 메서드명 - add_to_cart로 리다이렉트
        return self.add_to_cart(session_id, product_id, quantity, order_type, modifications, special_requests)

    def getCartDetails(self, session_id: str) -> Dict[str, Any]:
        # 레거시 메서드명 - get_cart_details로 리다이렉트
        return self.get_cart_details(session_id)

    def clearCart(self, session_id: str, cart_item_id: Optional[str] = None,
                  clear_all: bool = False) -> Dict[str, Any]:
        # 레거시 메서드명 - clear_cart로 리다이렉트
        return self.clear_cart(session_id, cart_item_id, clear_all)

    def updateCartItem(self, session_id: str, cart_item_id: str,
                      new_quantity: Optional[int] = None,
                      modifications: Optional[List[Dict]] = None,
                      action: str = "update_quantity") -> Dict[str, Any]:
        # 레거시 메서드명 - update_cart_item으로 리다이렉트
        return self.update_cart_item(session_id, cart_item_id, new_quantity, modifications, action)

    def processOrder(self, session_id: str, customer_info: Optional[Dict[str, str]] = None,
                    order_type: str = "takeout") -> Dict[str, Any]:
        # 레거시 메서드명 - process_order로 리다이렉트
        return self.process_order(session_id, customer_info, order_type)

    def getOrderDetails(self, order_id: str) -> Dict[str, Any]:
        # 레거시 메서드명 - get_order_details로 리다이렉트
        return self.get_order_details(order_id)