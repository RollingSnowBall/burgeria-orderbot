"""
Task 4.1: processOrder 함수 단위 테스트

테스트 함수:
- processOrder(session_id, customer_name, customer_phone, order_type)
"""

import sqlite3
import uuid
from db_functions import (
    addToCart,
    getCartDetails,
    processOrder,
    get_default_db_path
)


def clear_test_session(session_id: str):
    """테스트용 세션 데이터 초기화"""
    db_path = get_default_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Cart WHERE session_id = ?", (session_id,))
    cursor.execute("DELETE FROM Orders WHERE session_id = ?", (session_id,))

    # Order_Items도 함께 삭제 (외래키 관계)
    cursor.execute("""
    DELETE FROM Order_Items WHERE order_id IN (
        SELECT order_id FROM Orders WHERE session_id = ?
    )
    """, (session_id,))

    conn.commit()
    conn.close()


def print_cart(session_id: str, title: str = "장바구니 현황"):
    """장바구니 내용을 보기 좋게 출력"""
    cart = getCartDetails(session_id)
    print(f"\n{'='*50}")
    print(f"  {title}")
    print(f"{'='*50}")

    if cart['total_items'] == 0:
        print("  (비어있음)")
    else:
        for idx, item in enumerate(cart['items'], 1):
            set_info = f" [세트: {item['set_group_id']}]" if item['set_group_id'] else ""
            print(f"  {idx}. {item['product_name']}")
            print(f"     - 수량: {item['quantity']}개")
            print(f"     - 단가: {item['base_price']:,}원")
            print(f"     - 소계: {item['line_total']:,}원{set_info}")
        print(f"{'-'*50}")
        print(f"  총 {cart['total_items']}개 항목 | 합계: {cart['total_price']:,}원")
    print(f"{'='*50}\n")


def print_order(order_result: dict, title: str = "주문 완료"):
    """주문 결과를 보기 좋게 출력"""
    print(f"\n{'='*50}")
    print(f"  {title}")
    print(f"{'='*50}")

    if not order_result['success']:
        print(f"  [실패] {order_result['message']}")
    else:
        print(f"  주문번호: {order_result['order_number']}")
        print(f"  주문ID: {order_result['order_id']}")
        print(f"  총 항목: {order_result['total_items']}개")
        print(f"  총 금액: {order_result['total_price']:,}원")
        print(f"  주문시간: {order_result['created_at']}")
        print(f"  메시지: {order_result['message']}")
    print(f"{'='*50}\n")


def test_processOrder_basic():
    """테스트 1: 기본 주문 생성"""
    print("\n=== 테스트 1: 기본 주문 생성 ===")

    session_id = f"TEST_{uuid.uuid4().hex[:8]}"
    clear_test_session(session_id)

    # 장바구니에 상품 추가
    print(">> 한우불고기버거 2개, 콜라 1개 추가")
    addToCart(session_id, "A00001", quantity=2)  # 한우불고기버거 9000원
    addToCart(session_id, "C00001", quantity=1)  # 콜라 2000원
    print_cart(session_id, "주문 전 장바구니")

    # 주문 생성
    print(">> 주문 생성")
    order_result = processOrder(
        session_id,
        customer_name="홍길동",
        customer_phone="010-1234-5678",
        order_type="takeout"
    )
    print_order(order_result, "주문 완료")

    # 검증
    assert order_result['success'] == True
    assert order_result['total_items'] == 2
    assert order_result['total_price'] == 20000
    assert order_result['order_number'] is not None
    assert order_result['order_id'] is not None

    # 주문 후 장바구니 확인 (비어있어야 함)
    print_cart(session_id, "주문 후 장바구니")
    cart_after = getCartDetails(session_id)
    assert cart_after['total_items'] == 0

    clear_test_session(session_id)
    print("[PASS] 테스트 1 통과")


def test_processOrder_set_menu():
    """테스트 2: 세트 메뉴 주문"""
    print("\n=== 테스트 2: 세트 메뉴 주문 ===")

    session_id = f"TEST_{uuid.uuid4().hex[:8]}"
    clear_test_session(session_id)

    # 세트 메뉴 추가
    print(">> 한우불고기버거 세트 1개 추가")
    addToCart(session_id, "G00001", quantity=1)  # 한우불고기버거 세트
    print_cart(session_id, "주문 전 장바구니")

    # 주문 생성
    print(">> 주문 생성")
    order_result = processOrder(session_id)
    print_order(order_result, "주문 완료")

    # 검증
    assert order_result['success'] == True
    assert order_result['total_items'] == 3  # 버거 + 사이드 + 음료
    assert order_result['total_price'] == 13000

    # DB에서 주문 확인
    db_path = get_default_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT COUNT(*) FROM Order_Items WHERE order_id = ?
    """, (order_result['order_id'],))
    item_count = cursor.fetchone()[0]
    assert item_count == 3

    conn.close()
    clear_test_session(session_id)
    print("[PASS] 테스트 2 통과")


def test_processOrder_empty_cart():
    """테스트 3: 빈 장바구니로 주문 시도"""
    print("\n=== 테스트 3: 빈 장바구니로 주문 시도 ===")

    session_id = f"TEST_{uuid.uuid4().hex[:8]}"
    clear_test_session(session_id)

    print_cart(session_id, "빈 장바구니")

    # 빈 장바구니로 주문 시도
    print(">> 주문 시도")
    order_result = processOrder(session_id)
    print_order(order_result, "주문 결과")

    # 검증
    assert order_result['success'] == False
    assert "비어 있습니다" in order_result['message']

    print("[PASS] 테스트 3 통과")


def test_processOrder_multiple_items():
    """테스트 4: 여러 상품 혼합 주문"""
    print("\n=== 테스트 4: 여러 상품 혼합 주문 ===")

    session_id = f"TEST_{uuid.uuid4().hex[:8]}"
    clear_test_session(session_id)

    # 다양한 상품 추가
    print(">> 버거 2개, 사이드 1개, 음료 2개, 세트 1개 추가")
    addToCart(session_id, "A00001", quantity=2)  # 한우불고기버거
    addToCart(session_id, "B00001", quantity=1)  # 포테이토
    addToCart(session_id, "C00001", quantity=2)  # 콜라
    addToCart(session_id, "G00001", quantity=1)  # 한우불고기버거 세트
    print_cart(session_id, "주문 전 장바구니")

    # 주문 생성
    print(">> 주문 생성")
    order_result = processOrder(
        session_id,
        customer_name="김철수",
        customer_phone="010-9876-5432",
        order_type="delivery"
    )
    print_order(order_result, "주문 완료")

    # 검증
    assert order_result['success'] == True
    # 장바구니에는 6개 항목: 버거1, 사이드1, 음료1, 세트3개(버거+사이드+음료)
    # 하지만 장바구니에 동일 상품이 여러 번 추가되면 별도 항목으로 저장됨
    # 버거(2개), 사이드(1개), 음료(2개), 세트(3개) = 총 6개 항목
    assert order_result['total_items'] == 6
    # 18000(버거2) + 2000(사이드) + 4000(음료2) + 13000(세트) = 37000
    assert order_result['total_price'] == 37000

    # DB에서 주문 정보 확인
    db_path = get_default_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT customer_name, customer_phone, order_type, total_amount, status
    FROM Orders WHERE order_id = ?
    """, (order_result['order_id'],))
    order_info = cursor.fetchone()

    assert order_info[0] == "김철수"
    assert order_info[1] == "010-9876-5432"
    assert order_info[2] == "delivery"
    assert order_info[3] == 37000
    assert order_info[4] == "pending"

    conn.close()
    clear_test_session(session_id)
    print("[PASS] 테스트 4 통과")


def test_processOrder_order_number_increment():
    """테스트 5: 주문 번호 증가 확인"""
    print("\n=== 테스트 5: 주문 번호 증가 확인 ===")

    # 첫 번째 주문
    session_id_1 = f"TEST_{uuid.uuid4().hex[:8]}"
    clear_test_session(session_id_1)
    addToCart(session_id_1, "A00001", quantity=1)
    order_1 = processOrder(session_id_1)
    print(f"1번째 주문 번호: {order_1['order_number']}")

    # 두 번째 주문
    session_id_2 = f"TEST_{uuid.uuid4().hex[:8]}"
    clear_test_session(session_id_2)
    addToCart(session_id_2, "A00001", quantity=1)
    order_2 = processOrder(session_id_2)
    print(f"2번째 주문 번호: {order_2['order_number']}")

    # 검증: 주문 번호가 증가해야 함
    assert order_2['order_number'] > order_1['order_number']

    clear_test_session(session_id_1)
    clear_test_session(session_id_2)
    print("[PASS] 테스트 5 통과")


def run_all_tests():
    """모든 테스트 실행"""
    print("=" * 60)
    print("Task 4.1: processOrder 함수 테스트 시작")
    print("=" * 60)

    try:
        test_processOrder_basic()
        test_processOrder_set_menu()
        test_processOrder_empty_cart()
        test_processOrder_multiple_items()
        test_processOrder_order_number_increment()

        print("\n" + "=" * 60)
        print("[SUCCESS] 모든 테스트 통과! (5/5)")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n[FAIL] 테스트 실패: {e}")
        raise
    except Exception as e:
        print(f"\n[ERROR] 예외 발생: {e}")
        raise


if __name__ == "__main__":
    run_all_tests()
