"""
AI-powered conversation UI for order system
"""
from typing import Dict, List, Any

from core.order_bot import BurgeriaOrderBot
from llm_integration import BurgeriaLLMBot


class AIOrderUI:
    """AI-powered conversational order interface"""

    def __init__(self, order_bot: BurgeriaOrderBot):
        self.bot = order_bot
        self.llm_bot = BurgeriaLLMBot()
        self.session_id = "ai_customer_session"
        self.conversation_history = []

    def run(self):
        """Run the AI order system"""
        print("🍔 버거리아 AI 주문 시스템")
        print("자연스럽게 대화하면서 주문하세요!")
        print("예: '추천 메뉴 뭐가 있어요?', '매운 거 말고 담백한 버거 주세요', '콜라 말고 다른 음료로 바꿔주세요'")
        print("명령어: '장바구니', '주문 완료', '종료'\\n")

        while True:
            user_input = input("\\n고객: ").strip()

            if user_input in ["종료", "quit", "exit"]:
                print("직원: 이용해주셔서 감사합니다! 좋은 하루 되세요!")
                break

            elif user_input in ["장바구니", "cart"]:
                self._show_cart()
                continue

            elif user_input in ["주문 완료", "결제", "주문"]:
                self._process_order()
                continue

            # LLM 기반 AI 응답
            ai_response = self.llm_bot.chat(
                user_message=user_input,
                session_id=self.session_id,
                conversation_history=self.conversation_history
            )
            print(f"직원: {ai_response}")

            # 대화 히스토리 저장 (OpenAI 형식으로)
            self.conversation_history.append({"role": "user", "content": user_input})
            self.conversation_history.append({"role": "assistant", "content": ai_response})
            if len(self.conversation_history) > 20:  # 최근 20개 메시지만 유지 (10턴)
                self.conversation_history = self.conversation_history[-20:]

    def _show_cart(self):
        """Show cart contents"""
        cart = self.bot.get_cart_details(self.session_id)
        print(f"\\n직원: {cart['message']}")
        if cart['cart_items']:
            print("현재 주문하신 내용:")
            for item in cart['cart_items']:
                print(f"- {item['product_name']} x{item['quantity']}: {item['line_total']:,}원")
            print(f"총 금액: {cart['summary']['total_amount']:,}원")
            print("추가 주문이나 변경사항이 있으시면 말씀해주세요!")

    def _process_order(self):
        """Process final order"""
        order_result = self.bot.process_order(
            session_id=self.session_id,
            customer_info=None,
            order_type="takeout"
        )
        if order_result["success"]:
            print(f"직원: {order_result['message']}")
            print("맛있게 드세요!")
        else:
            print(f"직원: 죄송합니다. {order_result['error']}")

