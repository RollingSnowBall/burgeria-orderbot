"""
Task 2.2 통합 테스트: addToCart 세트 메뉴 지원 검증
"""

import sys
import os
import io
import sqlite3
import uuid

# Windows 인코딩 문제 해결
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# db_functions 모듈 import를 위한 경로 설정
sys.path.insert(0, os.path.dirname(__file__))

from db_functions import addToCart, get_default_db_path


def clear_test_cart(session_id: str, db_path: str):
    """테스트용 장바구니 초기화"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Cart WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()


def get_cart_items(session_id: str, db_path: str):
    """장바구니 조회"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT cart_item_id, product_id, product_name, order_type, quantity,
               base_price, line_total, set_group_id
        FROM Cart
        WHERE session_id = ?
        ORDER BY cart_item_id
    """, (session_id,))
    items = cursor.fetchall()
    conn.close()
    return items


def test_add_set_menu():
    """세트 메뉴 장바구니 추가 테스트"""
    print("\n=== Test 1: 세트 메뉴 추가 (G00001 - 한우불고기버거 세트) ===")

    db_path = get_default_db_path()
    session_id = f"TEST_{uuid.uuid4().hex[:8].upper()}"

    # 장바구니 초기화
    clear_test_cart(session_id, db_path)

    # 세트 메뉴 추가
    result = addToCart(session_id, "G00001", quantity=1)

    print(f"Success: {result['success']}")
    print(f"Product Name: {result['product_name']}")
    print(f"Set Group ID: {result.get('set_group_id', 'N/A')}")
    print(f"Base Price: {result.get('base_price', 0)}원")
    print(f"Line Total: {result.get('line_total', 0)}원")
    print(f"Components: {result.get('components_count', 0)}개")
    print(f"Message: {result['message']}")

    # DB에서 장바구니 확인
    cart_items = get_cart_items(session_id, db_path)
    print(f"\n장바구니 항목 개수: {len(cart_items)}")

    if cart_items:
        print("\n장바구니 상세:")
        for item in cart_items:
            print(f"  - {item[2]} (ID: {item[1]}, 타입: {item[3]}, "
                  f"수량: {item[4]}, 가격: {item[5]}원, 총액: {item[6]}원, "
                  f"세트그룹: {item[7]})")

    # 검증
    assert result['success'] == True, "세트 추가 실패"
    assert result['product_name'] == "한우불고기버거 세트", "상품명 불일치"
    assert result.get('components_count') == 3, "구성품이 3개여야 함"
    assert len(cart_items) == 3, f"장바구니에 3개 항목이 있어야 하는데 {len(cart_items)}개"

    # 모든 항목이 같은 set_group_id를 가져야 함
    set_group_ids = [item[7] for item in cart_items]
    assert len(set(set_group_ids)) == 1, "모든 구성품이 같은 set_group_id를 가져야 함"
    assert set_group_ids[0] is not None, "set_group_id가 None이면 안됨"

    # order_type이 'set'이어야 함
    order_types = [item[3] for item in cart_items]
    assert all(ot == 'set' for ot in order_types), "모든 항목의 order_type이 'set'이어야 함"

    # 정리
    clear_test_cart(session_id, db_path)

    print("\n✅ Test 1 통과!")
    return True


def test_add_single_item():
    """단품 메뉴 추가 (기존 기능 정상 작동 확인)"""
    print("\n=== Test 2: 단품 메뉴 추가 (A00001 - 한우불고기버거) ===")

    db_path = get_default_db_path()
    session_id = f"TEST_{uuid.uuid4().hex[:8].upper()}"

    clear_test_cart(session_id, db_path)

    # 단품 메뉴 추가
    result = addToCart(session_id, "A00001", quantity=2)

    print(f"Success: {result['success']}")
    print(f"Product Name: {result['product_name']}")
    print(f"Quantity: {result['quantity']}")
    print(f"Line Total: {result['line_total']}원")
    print(f"Message: {result['message']}")

    # DB 확인
    cart_items = get_cart_items(session_id, db_path)
    print(f"\n장바구니 항목 개수: {len(cart_items)}")

    # 검증
    assert result['success'] == True, "단품 추가 실패"
    assert result['product_name'] == "한우불고기버거", "상품명 불일치"
    assert result['quantity'] == 2, "수량 불일치"
    assert len(cart_items) == 1, "장바구니에 1개 항목이 있어야 함"
    assert cart_items[0][3] == "single", "order_type이 'single'이어야 함"
    assert cart_items[0][7] is None, "단품은 set_group_id가 None이어야 함"

    clear_test_cart(session_id, db_path)

    print("\n✅ Test 2 통과!")
    return True


def test_add_multiple_sets():
    """여러 세트 메뉴 추가 테스트"""
    print("\n=== Test 3: 여러 세트 메뉴 추가 ===")

    db_path = get_default_db_path()
    session_id = f"TEST_{uuid.uuid4().hex[:8].upper()}"

    clear_test_cart(session_id, db_path)

    # 첫 번째 세트 추가
    result1 = addToCart(session_id, "G00001", quantity=1)  # 한우불고기버거 세트
    set_group_1 = result1.get('set_group_id')

    # 두 번째 세트 추가
    result2 = addToCart(session_id, "G00009", quantity=1)  # 클래식 치즈버거 세트
    set_group_2 = result2.get('set_group_id')

    print(f"세트 1: {result1['product_name']} (그룹 ID: {set_group_1})")
    print(f"세트 2: {result2['product_name']} (그룹 ID: {set_group_2})")

    # DB 확인
    cart_items = get_cart_items(session_id, db_path)
    print(f"\n총 장바구니 항목 개수: {len(cart_items)}")

    # 검증
    assert result1['success'] == True, "세트 1 추가 실패"
    assert result2['success'] == True, "세트 2 추가 실패"
    assert len(cart_items) == 6, "장바구니에 6개 항목이 있어야 함 (각 세트당 3개)"
    assert set_group_1 != set_group_2, "각 세트는 다른 set_group_id를 가져야 함"

    # 각 세트별로 그룹핑 확인
    group_1_items = [item for item in cart_items if item[7] == set_group_1]
    group_2_items = [item for item in cart_items if item[7] == set_group_2]

    assert len(group_1_items) == 3, "세트 1의 구성품이 3개여야 함"
    assert len(group_2_items) == 3, "세트 2의 구성품이 3개여야 함"

    clear_test_cart(session_id, db_path)

    print("\n✅ Test 3 통과!")
    return True


def test_set_with_quantity():
    """세트 메뉴 수량 처리 테스트"""
    print("\n=== Test 4: 세트 메뉴 수량 2개 ===")

    db_path = get_default_db_path()
    session_id = f"TEST_{uuid.uuid4().hex[:8].upper()}"

    clear_test_cart(session_id, db_path)

    # 세트 메뉴 2개 추가
    result = addToCart(session_id, "G00001", quantity=2)

    print(f"Success: {result['success']}")
    print(f"Product Name: {result['product_name']}")
    print(f"Quantity: {result['quantity']}")
    print(f"Base Price: {result['base_price']}원")
    print(f"Line Total: {result['line_total']}원 (2개 기준)")

    # DB 확인
    cart_items = get_cart_items(session_id, db_path)

    print(f"\n장바구니 항목 개수: {len(cart_items)}")
    print("\n구성품별 수량:")
    for item in cart_items:
        print(f"  - {item[2]}: {item[4]}개")

    # 검증
    assert result['success'] == True, "세트 추가 실패"
    assert result['quantity'] == 2, "세트 수량이 2여야 함"
    assert len(cart_items) == 3, "구성품 항목은 3개여야 함"

    # 각 구성품의 수량이 2개씩이어야 함
    for item in cart_items:
        assert item[4] == 2, f"{item[2]}의 수량이 2여야 하는데 {item[4]}"

    # 총액 검증 (세트 가격 10200원 * 2)
    assert result['line_total'] == 10200 * 2, "총액 계산 오류"

    clear_test_cart(session_id, db_path)

    print("\n✅ Test 4 통과!")
    return True


def main():
    """모든 테스트 실행"""
    print("=" * 60)
    print("Task 2.2 addToCart 세트 메뉴 지원 통합 테스트")
    print("=" * 60)

    db_path = get_default_db_path()
    print(f"DB 경로: {db_path}")

    try:
        test_add_set_menu()
        test_add_single_item()
        test_add_multiple_sets()
        test_set_with_quantity()

        print("\n" + "=" * 60)
        print("🎉 모든 테스트 통과!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ 테스트 실패: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    main()
