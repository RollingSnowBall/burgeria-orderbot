"""
Task 3.4: updateSetItem 함수 단위 테스트

테스트 함수:
- updateSetItem(session_id, old_product_id, new_product_id, set_group_id, db_path)
- getSetMenusInCart(session_id, set_product_id, db_path)
"""

import sqlite3
import uuid
from db_functions import (
    addToCart,
    getCartDetails,
    updateSetItem,
    getSetMenusInCart,
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
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

    if cart['total_items'] == 0:
        print("  (비어있음)")
    else:
        for idx, item in enumerate(cart['items'], 1):
            set_info = f" [세트: {item['set_group_id']}]" if item['set_group_id'] else ""
            print(f"  {idx}. {item['product_name']}")
            print(f"     - 상품ID: {item['product_id']}")
            print(f"     - 수량: {item['quantity']}개")
            print(f"     - 단가: {item['base_price']:,}원")
            print(f"     - 소계: {item['line_total']:,}원{set_info}")
        print(f"{'-'*60}")
        print(f"  총 {cart['total_items']}개 항목 | 합계: {cart['total_price']:,}원")
    print(f"{'='*60}\n")


def print_update_result(result: dict, title: str = "교체 결과"):
    """updateSetItem 결과를 보기 좋게 출력"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

    print(f"  상태: {result['status']}")
    print(f"  성공: {result['success']}")
    print(f"  메시지: {result['message']}")

    if result['status'] == "UPDATED":
        print(f"\n  세트 그룹 ID: {result['set_group_id']}")
        print(f"  기존 상품: {result['old_product']['name']} ({result['old_product']['price']:,}원)")
        print(f"  새 상품: {result['new_product']['name']} ({result['new_product']['price']:,}원)")
        print(f"  가격 차이: {result['price_difference']:,}원")

    elif result['status'] == "MULTIPLE_SETS":
        print(f"\n  선택 가능한 세트: {len(result['sets'])}개")
        for idx, s in enumerate(result['sets'], 1):
            print(f"    {idx}. {s['set_name']} (그룹 ID: {s['set_group_id']})")

    print(f"{'='*60}\n")


def test_updateSetItem_single_set():
    """테스트 1: 단일 세트 자동 교체"""
    print("\n=== 테스트 1: 단일 세트 자동 교체 ===")

    session_id = f"TEST_{uuid.uuid4().hex[:8]}"
    clear_test_session(session_id)

    # 세트 메뉴 추가
    print(">> 한우불고기버거 세트 1개 추가")
    addToCart(session_id, "G00001", quantity=1)
    print_cart(session_id, "교체 전 장바구니")

    # 포테이토를 양념감자(칠리)로 교체
    print(">> 포테이토(B00001)를 양념감자 칠리(B00002)로 교체")
    result = updateSetItem(session_id, "B00001", "B00002")
    print_update_result(result, "교체 결과")

    # 검증
    assert result['status'] == "UPDATED"
    assert result['success'] == True
    assert result['old_product']['id'] == "B00001"
    assert result['new_product']['id'] == "B00002"
    assert result['price_difference'] == 500  # 2500 - 2000

    # 장바구니 확인
    print_cart(session_id, "교체 후 장바구니")
    cart = getCartDetails(session_id)

    # 포테이토가 없고 양념감자(칠리)가 있어야 함
    product_ids = [item['product_id'] for item in cart['items']]
    assert "B00001" not in product_ids
    assert "B00002" in product_ids

    # 총 금액 확인: 기존 13000 + 500 = 13500
    assert cart['total_price'] == 13500

    clear_test_session(session_id)
    print("[PASS] 테스트 1 통과")


def test_updateSetItem_multiple_sets():
    """테스트 2: 여러 세트가 있는 경우 (선택 필요)"""
    print("\n=== 테스트 2: 여러 세트가 있는 경우 ===")

    session_id = f"TEST_{uuid.uuid4().hex[:8]}"
    clear_test_session(session_id)

    # 동일한 세트 메뉴 2개 추가
    print(">> 한우불고기버거 세트 2개 추가")
    addToCart(session_id, "G00001", quantity=1)
    addToCart(session_id, "G00001", quantity=1)
    print_cart(session_id, "교체 전 장바구니")

    # set_group_id 없이 교체 시도 -> MULTIPLE_SETS 반환 예상
    print(">> set_group_id 없이 포테이토 교체 시도")
    result = updateSetItem(session_id, "B00001", "B00002")
    print_update_result(result, "교체 시도 결과")

    # 검증
    assert result['status'] == "MULTIPLE_SETS"
    assert result['success'] == False
    assert len(result['sets']) == 2
    assert "어떤 세트를 변경하시겠습니까" in result['message']

    # 특정 set_group_id로 교체
    first_set_group_id = result['sets'][0]['set_group_id']
    print(f">> 첫 번째 세트({first_set_group_id})의 포테이토를 양념감자로 교체")
    result2 = updateSetItem(session_id, "B00001", "B00002", set_group_id=first_set_group_id)
    print_update_result(result2, "특정 세트 교체 결과")

    # 검증
    assert result2['status'] == "UPDATED"
    assert result2['success'] == True
    assert result2['set_group_id'] == first_set_group_id

    # 장바구니 확인
    print_cart(session_id, "교체 후 장바구니")
    cart = getCartDetails(session_id)

    # 포테이토가 1개 남아있어야 함 (두 번째 세트)
    potato_count = sum(1 for item in cart['items'] if item['product_id'] == "B00001")
    assert potato_count == 1

    # 양념감자(칠리)가 1개 있어야 함 (첫 번째 세트)
    chili_count = sum(1 for item in cart['items'] if item['product_id'] == "B00002")
    assert chili_count == 1

    clear_test_session(session_id)
    print("[PASS] 테스트 2 통과")


def test_updateSetItem_no_matching_set():
    """테스트 3: 교체 대상 상품이 없는 경우"""
    print("\n=== 테스트 3: 교체 대상 상품이 없는 경우 ===")

    session_id = f"TEST_{uuid.uuid4().hex[:8]}"
    clear_test_session(session_id)

    # 세트 메뉴 추가
    print(">> 한우불고기버거 세트 추가")
    addToCart(session_id, "G00001", quantity=1)
    print_cart(session_id, "장바구니 현황")

    # 세트에 없는 상품으로 교체 시도
    print(">> 존재하지 않는 상품(B00999)을 교체 시도")
    result = updateSetItem(session_id, "B00999", "B00002")
    print_update_result(result, "교체 시도 결과")

    # 검증
    assert result['status'] == "ERROR"
    assert result['success'] == False
    assert "포함된 세트 메뉴가 없습니다" in result['message']

    clear_test_session(session_id)
    print("[PASS] 테스트 3 통과")


def test_updateSetItem_invalid_new_product():
    """테스트 4: 새 상품 ID가 유효하지 않은 경우"""
    print("\n=== 테스트 4: 새 상품 ID가 유효하지 않은 경우 ===")

    session_id = f"TEST_{uuid.uuid4().hex[:8]}"
    clear_test_session(session_id)

    # 세트 메뉴 추가
    print(">> 한우불고기버거 세트 추가")
    addToCart(session_id, "G00001", quantity=1)
    print_cart(session_id, "장바구니 현황")

    # 유효하지 않은 새 상품 ID로 교체 시도
    print(">> 포테이토를 존재하지 않는 상품(INVALID_ID)으로 교체 시도")
    result = updateSetItem(session_id, "B00001", "INVALID_ID")
    print_update_result(result, "교체 시도 결과")

    # 검증
    assert result['status'] == "ERROR"
    assert result['success'] == False
    assert "찾을 수 없습니다" in result['message']

    clear_test_session(session_id)
    print("[PASS] 테스트 4 통과")


def test_updateSetItem_price_decrease():
    """테스트 5: 가격이 낮아지는 교체"""
    print("\n=== 테스트 5: 가격이 낮아지는 교체 ===")

    session_id = f"TEST_{uuid.uuid4().hex[:8]}"
    clear_test_session(session_id)

    # 세트 메뉴 추가
    print(">> 한우불고기버거 세트 추가")
    addToCart(session_id, "G00001", quantity=1)
    print_cart(session_id, "교체 전 장바구니")

    # 포테이토(2000원)를 콘샐러드(1900원)로 교체
    print(">> 포테이토(B00001)를 콘샐러드(B00009)로 교체")
    result = updateSetItem(session_id, "B00001", "B00009")
    print_update_result(result, "교체 결과")

    # 검증
    assert result['status'] == "UPDATED"
    assert result['success'] == True
    assert result['price_difference'] == -100  # 1900 - 2000

    # 장바구니 확인
    print_cart(session_id, "교체 후 장바구니")
    cart = getCartDetails(session_id)

    # 총 금액 확인: 기존 13000 - 100 = 12900
    assert cart['total_price'] == 12900

    clear_test_session(session_id)
    print("[PASS] 테스트 5 통과")


def test_updateSetItem_invalid_set_group_id():
    """테스트 6: 유효하지 않은 set_group_id 제공"""
    print("\n=== 테스트 6: 유효하지 않은 set_group_id 제공 ===")

    session_id = f"TEST_{uuid.uuid4().hex[:8]}"
    clear_test_session(session_id)

    # 세트 메뉴 추가
    print(">> 한우불고기버거 세트 추가")
    addToCart(session_id, "G00001", quantity=1)
    print_cart(session_id, "장바구니 현황")

    # 존재하지 않는 set_group_id로 교체 시도
    print(">> 존재하지 않는 set_group_id로 교체 시도")
    result = updateSetItem(session_id, "B00001", "B00002", set_group_id="INVALID_SET_ID")
    print_update_result(result, "교체 시도 결과")

    # 검증
    assert result['status'] == "ERROR"
    assert result['success'] == False
    assert "찾을 수 없습니다" in result['message']

    clear_test_session(session_id)
    print("[PASS] 테스트 6 통과")


def test_getSetMenusInCart():
    """테스트 7: getSetMenusInCart 헬퍼 함수"""
    print("\n=== 테스트 7: getSetMenusInCart 헬퍼 함수 ===")

    session_id = f"TEST_{uuid.uuid4().hex[:8]}"
    clear_test_session(session_id)

    # 여러 세트 메뉴 추가
    print(">> 한우불고기버거 세트 2개 + 단품 버거 1개 추가")
    addToCart(session_id, "G00001", quantity=1)  # 한우불고기버거 세트
    addToCart(session_id, "G00001", quantity=1)  # 한우불고기버거 세트
    addToCart(session_id, "A00001", quantity=1)  # 단품 버거
    print_cart(session_id, "장바구니 현황")

    # 모든 세트 조회
    print(">> 모든 세트 메뉴 조회")
    result = getSetMenusInCart(session_id)

    print(f"\n{'='*60}")
    print(f"  세트 메뉴 조회 결과")
    print(f"{'='*60}")
    print(f"  성공: {result['success']}")
    print(f"  총 세트 수: {result['total_count']}")

    for idx, s in enumerate(result['sets'], 1):
        print(f"\n  [{idx}] {s['set_name']}")
        print(f"      - 세트 그룹 ID: {s['set_group_id']}")
        print(f"      - 총 가격: {s['total_price']:,}원")
        print(f"      - 구성품:")
        for item in s['items']:
            print(f"        * {item['product_name']} ({item['product_id']}) - {item['base_price']:,}원")

    print(f"{'='*60}\n")

    # 검증
    assert result['success'] == True
    assert result['total_count'] == 2
    assert len(result['sets']) == 2

    # 각 세트는 3개 항목을 가져야 함 (버거, 사이드, 음료)
    for s in result['sets']:
        assert len(s['items']) == 3

    clear_test_session(session_id)
    print("[PASS] 테스트 7 통과")


def test_updateSetItem_specific_set_product():
    """테스트 8: 특정 세트 상품이 포함된 세트만 조회 및 교체"""
    print("\n=== 테스트 8: 특정 세트 상품 필터링 ===")

    session_id = f"TEST_{uuid.uuid4().hex[:8]}"
    clear_test_session(session_id)

    # 다른 세트 메뉴들 추가
    print(">> 한우불고기버거 세트 + 치즈버거 세트 추가")
    addToCart(session_id, "G00001", quantity=1)  # 한우불고기버거 세트
    addToCart(session_id, "G00002", quantity=1)  # 치즈버거 세트
    print_cart(session_id, "장바구니 현황")

    # 한우불고기버거 세트만 조회
    print(">> 한우불고기버거 세트(G00001)만 조회")
    result = getSetMenusInCart(session_id, set_product_id="G00001")

    print(f"\n{'='*60}")
    print(f"  특정 세트 조회 결과")
    print(f"{'='*60}")
    print(f"  총 세트 수: {result['total_count']}")
    for s in result['sets']:
        print(f"  - {s['set_name']} (그룹 ID: {s['set_group_id']})")
    print(f"{'='*60}\n")

    # 검증
    assert result['success'] == True
    assert result['total_count'] == 1
    assert result['sets'][0]['set_product_id'] == "G00001"

    clear_test_session(session_id)
    print("[PASS] 테스트 8 통과")


def run_all_tests():
    """모든 테스트 실행"""
    print("=" * 60)
    print("Task 3.4: updateSetItem 함수 테스트 시작")
    print("=" * 60)

    try:
        test_updateSetItem_single_set()
        test_updateSetItem_multiple_sets()
        test_updateSetItem_no_matching_set()
        test_updateSetItem_invalid_new_product()
        test_updateSetItem_price_decrease()
        test_updateSetItem_invalid_set_group_id()
        test_getSetMenusInCart()
        test_updateSetItem_specific_set_product()

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
