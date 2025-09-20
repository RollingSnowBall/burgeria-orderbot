"""
Order service - handles order processing
"""
import uuid
from datetime import datetime
from typing import Dict, Optional, Any

from models.order import OrderItem, CustomerInfo
from database.repository import OrderRepository
from .cart_service import CartService


class OrderService:
    # 주문 관련 비즈니스 로직을 처리하는 서비스 클래스

    def __init__(self, order_repository: OrderRepository, cart_service: CartService):
        # OrderRepository와 CartService 인스턴스 주입
        self.order_repo = order_repository
        self.cart_service = cart_service

    def process_order(self, session_id: str, customer_info: Optional[Dict[str, str]] = None,
                     order_type: str = "takeout") -> Dict[str, Any]:
        # 장바구니 내용을 바탕으로 최종 주문 처리
        try:
            # 장바구니 내용 가져오기
            cart_details = self.cart_service.get_cart_details(session_id)
            if not cart_details["success"] or not cart_details["cart_items"]:
                return {
                    "success": False,
                    "error": "장바구니가 비어있습니다."
                }

            cart_items = cart_details["cart_items"]
            total_amount = cart_details["summary"]["total_amount"]

            # 주문 ID 생성 (날짜시간 기반)
            order_id = f"ORD_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # 예상 준비 시간 계산 (기본 10분 + 아이템당 3분)
            estimated_time = 10 + (len(cart_items) * 3)

            # 고객 정보 추출
            customer_name = customer_info.get("name", "") if customer_info else ""
            customer_phone = customer_info.get("phone", "") if customer_info else ""

            # 데이터베이스에 주문 생성
            if not self.order_repo.create_order(
                order_id, session_id, total_amount, order_type,
                customer_name, customer_phone, estimated_time
            ):
                return {
                    "success": False,
                    "error": "주문 생성 중 오류가 발생했습니다."
                }

            # 주문 아이템들을 데이터베이스에 삽입
            for cart_item in cart_items:
                order_item_id = str(uuid.uuid4())

                # 변경사항들을 Modification 객체로 변환 (딕셔너리 형태인 경우)
                modifications = []
                for mod in cart_item["modifications"]:
                    if isinstance(mod, dict):
                        from models.product import Modification
                        modifications.append(Modification(
                            type=mod.get("type", ""),
                            target_product_id=mod.get("target_product_id"),
                            new_product_id=mod.get("new_product_id"),
                            description=mod.get("description", ""),
                            price_change=mod.get("price_change", 0)
                        ))
                    else:
                        modifications.append(mod)

                order_item = OrderItem(
                    order_item_id=order_item_id,
                    order_id=order_id,
                    product_id=cart_item["product_id"],
                    product_name=cart_item["product_name"],
                    order_type=cart_item["order_type"],
                    quantity=cart_item["quantity"],
                    base_price=cart_item["base_price"],
                    modifications=modifications,
                    line_total=cart_item["line_total"],
                    special_requests=cart_item["special_requests"],
                    set_group_id=cart_item.get("set_group_id")
                )

                if not self.order_repo.add_order_item(order_item):
                    return {
                        "success": False,
                        "error": "주문 항목 저장 중 오류가 발생했습니다."
                    }

            # 성공적인 주문 후 장바구니 비우기
            clear_result = self.cart_service.clear_cart(session_id, clear_all=True)
            if not clear_result["success"]:
                # 경고 로그만 남기고 주문은 실패시키지 않음
                pass

            return {
                "success": True,
                "order_id": order_id,
                "estimated_time": estimated_time,
                "total_amount": total_amount,
                "order_summary": {
                    "items": cart_items,
                    "total_quantity": cart_details["summary"]["total_quantity"]
                },
                "message": f"주문이 완료되었습니다. 주문번호: {order_id}, 예상 대기시간: {estimated_time}분"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_order_details(self, order_id: str) -> Dict[str, Any]:
        # 특정 주문의 상세 정보 조회 (고객정보, 주문상품, 상태 등)
        try:
            # 데이터베이스에서 주문 상세 정보 가져오기
            order_details = self.order_repo.get_order_details(order_id)
            if not order_details:
                return {
                    "success": False,
                    "error": "주문을 찾을 수 없습니다."
                }

            return {
                "success": True,
                "order_info": order_details["order_info"],
                "order_items": order_details["order_items"],
                "message": f"주문 {order_id} 상세 정보를 조회했습니다."
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }