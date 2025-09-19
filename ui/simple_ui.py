"""
Simple text-based UI for order system
"""
import re
from typing import Dict, Any

from core.order_bot import BurgeriaOrderBot


class SimpleOrderUI:
    """Simple text-based order interface"""

    def __init__(self, order_bot: BurgeriaOrderBot):
        self.bot = order_bot
        self.session_id = "customer_session"

    def run(self):
        """Run the simple order system"""
        print("버거리아 키오스크")
        print("원하시는 메뉴를 말씀해주세요! (예: '한우불고기버거', '불고기 세트')")
        print("명령어: 장바구니, 주문, 비우기, 종료")

        while True:
            user_input = input("\\n무엇을 드릴까요? ").strip()

            if user_input in ["종료", "quit"]:
                print("이용해주셔서 감사합니다!")
                break

            elif user_input in ["장바구니", "cart"]:
                self._show_cart()

            elif user_input in ["비우기", "clear"]:
                self.bot.clear_cart(self.session_id, clear_all=True)
                print("장바구니를 비웠습니다!")

            elif user_input in ["주문", "order"]:
                self._process_order()

            else:
                self._handle_product_search(user_input)

    def _show_cart(self):
        """Show cart contents"""
        cart = self.bot.get_cart_details(self.session_id)
        print(f"\\n{cart['message']}")
        if cart['cart_items']:
            for item in cart['cart_items']:
                print(f"- {item['product_name']} x{item['quantity']}: {item['line_total']:,}원")
            print(f"총 금액: {cart['summary']['total_amount']:,}원")

    def _process_order(self):
        """Process final order"""
        order_result = self.bot.process_order(
            session_id=self.session_id,
            customer_info=None,
            order_type="takeout"
        )

        if order_result["success"]:
            print(f"주문 완료! {order_result['message']}")
        else:
            print(f"주문 실패: {order_result['error']}")

    def _handle_product_search(self, user_input: str):
        """Handle product search and ordering"""
        # 자연어 처리로 제품 검색 및 주문 처리
        search_result = self.bot.find_product(user_input, limit=5)

        if search_result["success"] and search_result["matches"]:
            # 단품과 세트 분리
            single_items = []
            set_items = []

            for match in search_result["matches"]:
                if match['product_type'] == 'set':
                    set_items.append(match)
                else:
                    single_items.append(match)

            print(f"\\n'{user_input}' 검색 결과:")

            if single_items:
                print("\\n[단품]")
                for item in single_items:
                    print(f"- {item['product_name']} ({item['price']:,}원)")

            if set_items:
                print("\\n[세트]")
                for item in set_items:
                    print(f"- {item['product_name']} ({item['price']:,}원)")

            # 다음 입력 대기
            print("\\n어떤 것으로 하시겠어요? (예: '더블 한우불고기버거 세트 2개', '한우불고기버거 단품')")

            # 두 번째 입력 처리 (주문 확정)
            self._handle_order_confirmation(search_result)

        else:
            print("해당 메뉴를 찾을 수 없습니다. 다른 키워드로 검색해보세요.")

    def _handle_order_confirmation(self, search_result: Dict[str, Any]):
        """Handle order confirmation after product search"""
        order_input = input("").strip()

        if not order_input:
            return

        # 입력에서 제품 매칭
        quantity = 1

        # 수량 추출
        qty_match = re.search(r'(\\d+)개', order_input)
        if qty_match:
            quantity = int(qty_match.group(1))

        # 제품 매칭 (가장 유사한 것 선택)
        best_match = None
        best_score = 0

        all_items = search_result["matches"]
        for item in all_items:
            # 제품명 매칭
            score = self.bot.similarity(order_input, item['product_name'])
            if score > best_score:
                best_score = score
                best_match = item

        if best_match and best_score > 0.3:
            selected_item = best_match
            print(f"\\n{selected_item['product_name']} {quantity}개를 선택하셨습니다.")

            # 세트 주문 처리
            if selected_item['product_type'] == 'set':
                self._handle_set_order(selected_item, quantity)
            else:
                self._handle_single_order(selected_item, quantity)
        else:
            print("선택하신 상품을 찾을 수 없습니다. 다시 말씀해주세요.")

    def _handle_set_order(self, selected_item: Dict[str, Any], quantity: int):
        """Handle set order with modifications"""
        set_options = self.bot.get_set_change_options(selected_item['product_id'])
        modifications = []

        if set_options["success"]:
            print(f"\\n{selected_item['product_name']} 기본 구성:")
            components = set_options["current_components"]
            for comp_type, comp in components.items():
                if comp:
                    print(f"- {comp['product_name']}")

            # 변경사항 확인
            change_input = input("\\n변경하고 싶은 음료나 사이드가 있으시면 말씀해주세요 (없으면 엔터): ").strip()

            if change_input:
                beverage_options = set_options["change_options"]["beverage"]
                sides_options = set_options["change_options"]["sides"]

                # 음료 변경 매칭
                for bev in beverage_options:
                    if self.bot.similarity(change_input, bev['product_name']) > 0.5:
                        modifications.append({
                            "type": "change_component",
                            "target_product_id": components['beverage']['product_id'],
                            "new_product_id": bev['product_id']
                        })
                        print(f"음료를 {bev['product_name']}로 변경합니다.")
                        break

                # 사이드 변경 매칭
                for side in sides_options:
                    if self.bot.similarity(change_input, side['product_name']) > 0.5:
                        modifications.append({
                            "type": "change_component",
                            "target_product_id": components['sides']['product_id'],
                            "new_product_id": side['product_id']
                        })
                        print(f"사이드를 {side['product_name']}로 변경합니다.")
                        break

        # 세트를 장바구니에 추가
        result = self.bot.add_to_cart(
            session_id=self.session_id,
            product_id=selected_item['product_id'],
            quantity=quantity,
            order_type="set",
            modifications=modifications
        )

        self._show_add_result(result)

    def _handle_single_order(self, selected_item: Dict[str, Any], quantity: int):
        """Handle single item order"""
        # 단품을 장바구니에 추가
        result = self.bot.add_to_cart(
            session_id=self.session_id,
            product_id=selected_item['product_id'],
            quantity=quantity,
            order_type="single"
        )

        self._show_add_result(result)

    def _show_add_result(self, result: Dict[str, Any]):
        """Show result of adding item to cart"""
        if result["success"]:
            print(f"장바구니에 추가했습니다! {result['message']}")
            print("계속 주문하시거나 '장바구니'로 확인, '주문'으로 결제하세요.")
        else:
            print(f"오류: {result['error']}")