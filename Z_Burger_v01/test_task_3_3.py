"""
Task 3.3: 장바구니 관리 함수 단위 테스트

테스트 함수:
- getCartDetails(session_id)
- updateCartItem(cart_item_id, quantity)
- clearCart(session_id)
"""

import sqlite3
import uuid
from db_functions import (
    addToCart,
    getCartDetails,
    updateCartItem,
    clearCart,
    get_default_db_path
)


def clear_test_session(session_id: str):
    """테스트용 세션 데이터 초기화"""
    db_path = get_default_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Cart WHERE session_id = ?", (session_id,))
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


def test_getCartDetails_empty():
    """테스트 1: 빈 장바구니 조회"""
    print("\n=== 테스트 1: 빈 장바구니 조회 ===")

    session_id = f"TEST_{uuid.uuid4().hex[:8]}"
    clear_test_session(session_id)

    print_cart(session_id, "장바구니 조회 결과")

    result = getCartDetails(session_id)

    print(f"Success: {result['success']}")
    print(f"Total Items: {result['total_items']}")
    print(f"Total Price: {result['total_price']}")
    print(f"Message: {result['message']}")

    assert result['success'] == True
    assert result['total_items'] == 0
    assert result['total_price'] == 0
    assert result['message'] == "장바구니가 비어 있습니다."

    print("[PASS] 테스트 1 통과")


def test_getCartDetails_with_items():
    """테스트 2: 장바구니에 상품이 있을 때 조회"""
    print("\n=== 테스트 2: 장바구니에 상품이 있을 때 조회 ===")

    session_id = f"TEST_{uuid.uuid4().hex[:8]}"
    clear_test_session(session_id)

    # 단품 2개 추가
    print(">> 한우불고기버거 2개 추가")
    addToCart(session_id, "A00001", quantity=2)  # 한우불고기버거 9000원
    print_cart(session_id, "상품 추가 후")

    print(">> 포테이토 1개 추가")
    addToCart(session_id, "B00001", quantity=1)  # 포테이토 2000원
    print_cart(session_id, "상품 추가 후")

    result = getCartDetails(session_id)

    print(f"Success: {result['success']}")
    print(f"Total Items: {result['total_items']}")
    print(f"Total Price: {result['total_price']}")

    assert result['success'] == True
    assert result['total_items'] == 2
    assert result['total_price'] == 18000 + 2000  # 20000원

    clear_test_session(session_id)
    print("[PASS] 테스트 2 통과")


def test_getCartDetails_with_set():
    """테스트 3: 세트 메뉴가 포함된 장바구니 조회"""
    print("\n=== 테스트 3: 세트 메뉴가 포함된 장바구니 조회 ===")

    session_id = f"TEST_{uuid.uuid4().hex[:8]}"
    clear_test_session(session_id)

    # 세트 메뉴 추가
    print(">> 한우불고기버거 세트 1개 추가")
    set_result = addToCart(session_id, "G00001", quantity=1)  # 한우불고기버거 세트 10200원
    print_cart(session_id, "세트 메뉴 추가 후")

    result = getCartDetails(session_id)

    print(f"Success: {result['success']}")
    print(f"Total Items: {result['total_items']}")
    print(f"Total Price: {result['total_price']}")
    print(f"Set Group ID: {set_result['set_group_id']}")

    assert result['success'] == True
    assert result['total_items'] == 3  # 버거 + 사이드 + 음료
    # 세트 메뉴는 구성품 개별 가격의 합계로 저장됨 (9000 + 2000 + 2000 = 13000)
    assert result['total_price'] == 13000

    # 모든 항목이 같은 set_group_id를 가지는지 확인
    set_group_ids = [item['set_group_id'] for item in result['items']]
    assert len(set(set_group_ids)) == 1  # 모두 동일한 set_group_id

    clear_test_session(session_id)
    print("[PASS] 테스트 3 통과")


def test_updateCartItem_quantity():
    """테스트 4: 장바구니 항목 수량 변경"""
    print("\n=== 테스트 4: 장바구니 항목 수량 변경 ===")

    session_id = f"TEST_{uuid.uuid4().hex[:8]}"
    clear_test_session(session_id)

    # 상품 추가
    print(">> 한우불고기버거 1개 추가")
    add_result = addToCart(session_id, "A00001", quantity=1)  # 한우불고기버거 9000원
    cart_item_id = add_result['cart_item_id']
    print_cart(session_id, "상품 추가 후")

    # 수량 변경 (1 -> 3)
    print(">> 수량을 1개에서 3개로 변경")
    update_result = updateCartItem(cart_item_id, 3)
    print_cart(session_id, "수량 변경 후")

    print(f"Success: {update_result['success']}")
    print(f"Product: {update_result['product_name']}")
    print(f"Old Quantity: {update_result['old_quantity']}")
    print(f"New Quantity: {update_result['new_quantity']}")
    print(f"New Line Total: {update_result['new_line_total']}")
    print(f"Message: {update_result['message']}")

    assert update_result['success'] == True
    assert update_result['old_quantity'] == 1
    assert update_result['new_quantity'] == 3
    assert update_result['new_line_total'] == 9000 * 3  # 27000원

    # 장바구니 조회로 검증
    cart = getCartDetails(session_id)
    assert cart['items'][0]['quantity'] == 3
    assert cart['items'][0]['line_total'] == 27000

    clear_test_session(session_id)
    print("[PASS] 테스트 4 통과")


def test_updateCartItem_delete():
    """테스트 5: 장바구니 항목 삭제 (수량 0)"""
    print("\n=== 테스트 5: 장바구니 항목 삭제 (수량 0) ===")

    session_id = f"TEST_{uuid.uuid4().hex[:8]}"
    clear_test_session(session_id)

    # 상품 2개 추가
    print(">> 한우불고기버거 1개, 포테이토 1개 추가")
    add_result1 = addToCart(session_id, "A00001", quantity=1)  # 한우불고기버거
    add_result2 = addToCart(session_id, "B00001", quantity=1)  # 포테이토
    print_cart(session_id, "상품 추가 후")

    # 첫 번째 항목 삭제 (수량 0으로 설정)
    print(">> 한우불고기버거 삭제 (수량 0)")
    delete_result = updateCartItem(add_result1['cart_item_id'], 0)
    print_cart(session_id, "항목 삭제 후")

    print(f"Success: {delete_result['success']}")
    print(f"Product: {delete_result['product_name']}")
    print(f"Message: {delete_result['message']}")

    assert delete_result['success'] == True
    assert delete_result['new_quantity'] == 0
    assert "삭제" in delete_result['message']

    # 장바구니 조회로 검증
    cart_after = getCartDetails(session_id)

    assert cart_after['total_items'] == 1  # 1개만 남음
    assert cart_after['items'][0]['product_name'] == "포테이토 (미디움)"

    clear_test_session(session_id)
    print("[PASS] 테스트 5 통과")


def test_updateCartItem_invalid_id():
    """테스트 6: 존재하지 않는 장바구니 항목 수정 시도"""
    print("\n=== 테스트 6: 존재하지 않는 장바구니 항목 수정 시도 ===")

    result = updateCartItem("INVALID_CART_ID", 2)

    print(f"Success: {result['success']}")
    print(f"Message: {result['message']}")

    assert result['success'] == False
    assert "찾을 수 없습니다" in result['message']

    print("[PASS] 테스트 6 통과")


def test_clearCart():
    """테스트 7: 장바구니 전체 비우기"""
    print("\n=== 테스트 7: 장바구니 전체 비우기 ===")

    session_id = f"TEST_{uuid.uuid4().hex[:8]}"
    clear_test_session(session_id)

    # 상품 여러 개 추가
    print(">> 한우불고기버거 2개, 포테이토 1개, 콜라 1개 추가")
    addToCart(session_id, "A00001", quantity=2)  # 한우불고기버거
    addToCart(session_id, "B00001", quantity=1)  # 포테이토
    addToCart(session_id, "C00001", quantity=1)  # 콜라
    print_cart(session_id, "비우기 전")

    # 장바구니 비우기
    print(">> 장바구니 전체 비우기")
    clear_result = clearCart(session_id)
    print_cart(session_id, "비우기 후")

    print(f"Success: {clear_result['success']}")
    print(f"Deleted Count: {clear_result['deleted_count']}")
    print(f"Message: {clear_result['message']}")

    assert clear_result['success'] == True
    assert clear_result['deleted_count'] == 3

    # 장바구니 조회로 검증
    cart_after = getCartDetails(session_id)

    assert cart_after['total_items'] == 0
    assert cart_after['total_price'] == 0

    print("[PASS] 테스트 7 통과")


def test_clearCart_empty():
    """테스트 8: 이미 비어있는 장바구니 비우기"""
    print("\n=== 테스트 8: 이미 비어있는 장바구니 비우기 ===")

    session_id = f"TEST_{uuid.uuid4().hex[:8]}"
    clear_test_session(session_id)

    print_cart(session_id, "비우기 전 (빈 상태)")

    print(">> 빈 장바구니를 비우기 시도")
    result = clearCart(session_id)

    print(f"Success: {result['success']}")
    print(f"Deleted Count: {result['deleted_count']}")
    print(f"Message: {result['message']}")

    assert result['success'] == True
    assert result['deleted_count'] == 0
    assert "이미 비어 있습니다" in result['message']

    print("[PASS] 테스트 8 통과")


def run_all_tests():
    """모든 테스트 실행"""
    print("=" * 60)
    print("Task 3.3: 장바구니 관리 함수 테스트 시작")
    print("=" * 60)

    try:
        test_getCartDetails_empty()
        test_getCartDetails_with_items()
        test_getCartDetails_with_set()
        test_updateCartItem_quantity()
        test_updateCartItem_delete()
        test_updateCartItem_invalid_id()
        test_clearCart()
        test_clearCart_empty()

        print("\n" + "=" * 60)
        print("[SUCCESS] 모든 테스트 통과! (8/8)")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n[FAIL] 테스트 실패: {e}")
        raise
    except Exception as e:
        print(f"\n[ERROR] 예외 발생: {e}")
        raise


if __name__ == "__main__":
    run_all_tests()
