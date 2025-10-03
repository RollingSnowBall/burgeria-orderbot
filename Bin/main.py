"""
Main entry point for Burgeria Order Bot
"""
import sys
from core.order_bot import BurgeriaOrderBot
from ui.simple_ui import SimpleOrderUI
from ui.ai_ui import AIOrderUI


def main():
    # 프로그램의 메인 진입점 - 사용자에게 UI 선택 메뉴 제공
    print("=== 버거리아 주문 시스템 ===")
    print("1. 간단한 텍스트 주문 시스템")
    print("2. AI 대화형 주문 시스템")
    print("3. 테스트 모드")
    print("4. 종료")

    while True:
        choice = input("\\n선택하세요 (1-4): ").strip()

        if choice == "1":
            # 간단한 텍스트 기반 주문 시스템 실행
            print("\\n간단한 텍스트 주문 시스템을 시작합니다...")
            bot = BurgeriaOrderBot()
            ui = SimpleOrderUI(bot)
            ui.run()
            break

        elif choice == "2":
            # AI 대화형 주문 시스템 실행
            print("\\nAI 대화형 주문 시스템을 시작합니다...")
            bot = BurgeriaOrderBot()
            ui = AIOrderUI(bot)
            ui.run()
            break

        elif choice == "3":
            # 테스트 모드 실행 (개발/디버깅용)
            print("\\n테스트 모드를 시작합니다...")
            run_test_mode()
            break

        elif choice == "4":
            # 프로그램 종료
            print("프로그램을 종료합니다.")
            sys.exit(0)

        else:
            print("잘못된 선택입니다. 1-4 중에서 선택해주세요.")


def run_test_mode():
    # 테스트 모드 실행 - 시스템의 모든 기능을 테스트
    bot = BurgeriaOrderBot()
    session_id = "test_session_001"

    print("\\n=== Burgeria Order Bot Test (Updated) ===")

    # 기존 장바구니 비우기
    bot.clear_cart(session_id, clear_all=True)

    # 데이터베이스 상태 확인 (세트 구성품 데이터 존재 여부)
    print("\\n0. 데이터베이스 상태 확인:")
    test_set = bot.get_set_components("G00001")
    if not test_set:
        print("⚠️  Set_Items 테이블에 데이터가 없습니다.")
        print("   다음 명령으로 데이터를 로드하세요:")
        print("   sqlite3 BurgeriaDB.db < SET.sql")
        return
    else:
        print(f"✅ 세트 구성품 {len(test_set)}개 발견")

    # 테스트 1: 제품 검색 기능 테스트
    print("\\n1. 제품 검색 테스트:")
    result = bot.find_product("한우불고기", category="burger")
    print(f"검색 결과: {result['total_found']}개 발견")
    for match in result["matches"]:
        print(f"- {match['product_name']} ({match['product_id']}) - {match['price']}원")

    # 테스트 2: 세트 변경 옵션 기능 테스트
    print("\\n2. 세트 변경 옵션 테스트:")
    set_options = bot.get_set_change_options("G00001")  # 한우불고기버거 세트
    if set_options["success"]:
        print("현재 세트 구성:")
        for comp_type, comp in set_options["current_components"].items():
            if comp:
                print(f"- {comp_type}: {comp['product_name']} ({comp['price']}원)")

        print("\\n변경 가능한 음료 (처음 3개):")
        for beverage in set_options["change_options"]["beverage"][:3]:
            print(f"- {beverage['product_name']} ({beverage['price']}원)")

        print("\\n변경 가능한 사이드 (처음 3개):")
        for side in set_options["change_options"]["sides"][:3]:
            print(f"- {side['product_name']} ({side['price']}원)")

    # 테스트 3: 세트 주문 및 구성품 변경 기능 테스트
    print("\\n3. 세트 주문 테스트 (음료 변경):")
    set_result = bot.add_to_cart(
        session_id=session_id,
        product_id="G00001",  # 한우불고기버거 세트
        quantity=1,
        order_type="set",
        modifications=[{
            "type": "change_component",
            "target_product_id": "C00001",  # 기본 콜라
            "new_product_id": "C00007"      # 아이스티로 변경
        }]
    )
    if set_result.get("success"):
        print(f"세트 추가 결과: {set_result.get('message', '세트가 장바구니에 추가되었습니다.')}")
        print(f"총 금액: {set_result['price_breakdown']['line_total']}원")
        if set_result['item_details']['modifications']:
            print("변경사항:")
            for mod in set_result['item_details']['modifications']:
                print(f"- {mod['description']}: {mod['price_change']:+d}원")
    else:
        print(f"세트 추가 실패: {set_result.get('error', '알 수 없는 오류')}")

    # 테스트 4: 단품 주문 및 토핑 추가 기능 테스트
    print("\\n4. 단품 주문 테스트 (토핑 추가):")
    single_result = bot.add_to_cart(
        session_id=session_id,
        product_id="A00003",  # 리아 불고기버거
        quantity=1,
        order_type="single",
        modifications=[{
            "type": "add_topping",
            "target_product_id": "A00003",
            "new_product_id": "D00002"  # 치즈토핑
        }]
    )
    if single_result.get("success"):
        print(f"단품 추가 결과: {single_result.get('message', '단품이 장바구니에 추가되었습니다.')}")
        print(f"총 금액: {single_result['price_breakdown']['line_total']}원")
    else:
        print(f"단품 추가 실패: {single_result.get('error', '알 수 없는 오류')}")

    # 테스트 5: 장바구니 조회 기능 테스트
    print("\\n5. 장바구니 조회 테스트:")
    cart = bot.get_cart_details(session_id)
    print(f"장바구니 상태: {cart['message']}")
    print(f"총 금액: {cart['summary']['total_amount']}원")
    print("\\n장바구니 상세:")
    for item in cart['cart_items']:
        print(f"- {item['product_name']} x{item['quantity']}: {item['line_total']}원")
        if item['modifications']:
            for mod in item['modifications']:
                print(f"  └ {mod['description']}: {mod['price_change']:+d}원")

    # 테스트 6: 주문 처리 기능 테스트
    print("\\n6. 주문 처리 테스트:")
    order_result = bot.process_order(
        session_id=session_id,
        customer_info={"name": "홍길동", "phone": "010-1234-5678"},
        order_type="takeout"
    )
    order_id = None
    if order_result["success"]:
        print(f"주문 완료: {order_result['message']}")
        order_id = order_result["order_id"]
    else:
        print(f"주문 실패: {order_result['error']}")

    # 테스트 7: 주문 후 장바구니 비워짐 확인 테스트
    print("\\n7. 주문 후 장바구니 확인:")
    empty_cart = bot.get_cart_details(session_id)
    print(f"주문 후 장바구니: {empty_cart['message']}")

    # 테스트 8: 주문 상세 정보 조회 기능 테스트
    if order_id:
        print(f"\\n8. 주문 상세 조회 테스트 (주문번호: {order_id}):")
        order_details = bot.get_order_details(order_id)
        if order_details["success"]:
            order_info = order_details["order_info"]
            print(f"고객명: {order_info['customer_name']}")
            print(f"전화번호: {order_info['customer_phone']}")
            print(f"총 금액: {order_info['total_amount']}원")
            print(f"예상 시간: {order_info['estimated_time']}분")
            print(f"주문 상태: {order_info['status']}")

            print("\\n주문 상품 목록:")
            for item in order_details["order_items"]:
                print(f"- {item['product_name']} x{item['quantity']}: {item['line_total']}원")
                if item['modifications']:
                    for mod in item['modifications']:
                        print(f"  └ {mod['description']}: {mod['price_change']:+d}원")
        else:
            print(f"주문 조회 실패: {order_details['error']}")

    print("\\n=== 테스트 완료 ===")


if __name__ == "__main__":
    main()