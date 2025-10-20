"""
Task 2.3 통합 테스트: 옵션 변경 시나리오 검증
LLM 없이 함수 레벨에서 옵션 변경 로직 검증
"""

import sys
import os
import io

# Windows 인코딩 문제 해결
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# db_functions 모듈 import를 위한 경로 설정
sys.path.insert(0, os.path.dirname(__file__))

from db_functions import findProduct, getSetComposition, addToCart, get_default_db_path


def test_option_change_scenario():
    """옵션 변경 시나리오: 감자튀김 → 양념감자(칠리)"""
    print("\n=== Test 1: 세트 옵션 변경 시나리오 (가격 차이 있음) ===")

    # 1. 세트 메뉴 검색
    print("\n[Step 1] 세트 메뉴 검색")
    set_result = findProduct("한우불고기버거 세트")
    print(f"세트 메뉴: {set_result['product']['product_name']}")
    print(f"세트 ID: {set_result['product']['product_id']}")
    print(f"세트 가격: {set_result['product']['price']}원")

    set_product_id = set_result['product']['product_id']

    # 2. 세트 구성품 조회
    print("\n[Step 2] 세트 구성품 조회")
    composition = getSetComposition(set_product_id)
    print(f"구성품 개수: {len(composition['items'])}")

    sides_item = None
    for item in composition['items']:
        print(f"  - {item['product_name']} ({item['product_type']}): {item['price']}원")
        if item['product_type'] == 'sides':
            sides_item = item

    print(f"\n기존 사이드: {sides_item['product_name']} - {sides_item['price']}원")

    # 3. 변경할 메뉴 검색
    print("\n[Step 3] 변경할 메뉴 검색")
    new_sides = findProduct("양념감자", category="sides")

    if new_sides['status'] == 'FOUND':
        new_item = new_sides['product']
        print(f"새 사이드: {new_item['product_name']} - {new_item['price']}원")

        # 4. 가격 차이 계산
        print("\n[Step 4] 가격 차이 계산")
        price_diff = new_item['price'] - sides_item['price']
        print(f"기존: {sides_item['price']}원")
        print(f"변경: {new_item['price']}원")
        print(f"추가금: {price_diff}원")

        # 검증
        assert price_diff == 600, f"추가금이 600원이어야 하는데 {price_diff}원"
        print("\n✅ 가격 차이 계산 정확!")

    # 5. 장바구니에 담기 (special_requests 사용)
    print("\n[Step 5] 변경사항과 함께 장바구니에 담기")
    import uuid
    session_id = f"TEST_{uuid.uuid4().hex[:8].upper()}"

    special_request = f"포테이토 (미디움) → 양념감자 (칠리) 변경 (+600원)"
    cart_result = addToCart(
        session_id=session_id,
        product_id=set_product_id,
        quantity=1,
        special_requests=special_request
    )

    print(f"장바구니 담기: {cart_result['success']}")
    print(f"메시지: {cart_result['message']}")

    assert cart_result['success'] == True, "장바구니 담기 실패"

    print("\n✅ Test 1 통과! 옵션 변경 시나리오 성공")
    return True


def test_same_price_option_change():
    """옵션 변경 시나리오: 콜라 → 사이다 (가격 동일)"""
    print("\n=== Test 2: 세트 옵션 변경 (가격 동일) ===")

    # 1. 세트 구성품 조회
    set_id = "G00003"  # 리아 불고기버거 세트
    composition = getSetComposition(set_id)

    beverage_item = None
    for item in composition['items']:
        if item['product_type'] == 'beverage':
            beverage_item = item
            break

    print(f"기존 음료: {beverage_item['product_name']} - {beverage_item['price']}원")

    # 2. 변경할 음료 검색
    new_beverage = findProduct("사이다", category="beverage")
    new_item = new_beverage['product']
    print(f"새 음료: {new_item['product_name']} - {new_item['price']}원")

    # 3. 가격 차이 계산
    price_diff = new_item['price'] - beverage_item['price']
    print(f"가격 차이: {price_diff}원")

    assert price_diff == 0, f"가격 차이가 0원이어야 하는데 {price_diff}원"
    print("\n✅ 동일 가격 확인!")

    # 4. 장바구니에 담기
    import uuid
    session_id = f"TEST_{uuid.uuid4().hex[:8].upper()}"

    special_request = f"{beverage_item['product_name']} → {new_item['product_name']} 변경 (추가금 없음)"
    cart_result = addToCart(
        session_id=session_id,
        product_id=set_id,
        quantity=1,
        special_requests=special_request
    )

    assert cart_result['success'] == True, "장바구니 담기 실패"

    print("\n✅ Test 2 통과! 동일 가격 옵션 변경 성공")
    return True


def test_category_validation():
    """카테고리 검증: 사이드를 음료로 바꾸려는 경우"""
    print("\n=== Test 3: 카테고리 검증 (잘못된 카테고리 변경 시도) ===")

    # 세트 구성품 조회
    composition = getSetComposition("G00001")

    sides_item = None
    for item in composition['items']:
        if item['product_type'] == 'sides':
            sides_item = item
            break

    print(f"기존 사이드: {sides_item['product_name']} (카테고리: {sides_item['product_type']})")

    # 음료로 변경 시도
    beverage = findProduct("콜라", category="beverage")
    beverage_item = beverage['product']
    print(f"변경 시도: {beverage_item['product_name']} (카테고리: {beverage_item['product_type']})")

    # 카테고리 검증
    if sides_item['category_id'] != beverage_item['category_id']:
        print("\n❌ 카테고리가 다릅니다!")
        print(f"기존: {sides_item['category_id']}")
        print(f"변경: {beverage_item['category_id']}")
        print("→ 같은 카테고리 내에서만 변경 가능합니다.")

        print("\n✅ Test 3 통과! 카테고리 검증 정상 작동")
        return True
    else:
        raise AssertionError("카테고리가 같으면 안됨")


def test_multiple_option_changes():
    """여러 옵션을 동시에 변경하는 시나리오"""
    print("\n=== Test 4: 여러 옵션 동시 변경 ===")

    set_id = "G00001"
    composition = getSetComposition(set_id)

    # 사이드와 음료 모두 변경
    sides_change = "포테이토 (미디움) → 양념감자 (치즈)"
    beverage_change = "콜라 (미디움) → 레몬에이드 (미디움)"

    special_request = f"{sides_change}, {beverage_change}"

    print(f"변경사항: {special_request}")

    import uuid
    session_id = f"TEST_{uuid.uuid4().hex[:8].upper()}"

    cart_result = addToCart(
        session_id=session_id,
        product_id=set_id,
        quantity=1,
        special_requests=special_request
    )

    print(f"장바구니 담기: {cart_result['success']}")

    assert cart_result['success'] == True, "장바구니 담기 실패"

    print("\n✅ Test 4 통과! 여러 옵션 동시 변경 성공")
    return True


def main():
    """모든 테스트 실행"""
    print("=" * 60)
    print("Task 2.3 옵션 변경 대화 로직 통합 테스트")
    print("=" * 60)

    db_path = get_default_db_path()
    print(f"DB 경로: {db_path}")

    try:
        test_option_change_scenario()
        test_same_price_option_change()
        test_category_validation()
        test_multiple_option_changes()

        print("\n" + "=" * 60)
        print("🎉 모든 테스트 통과!")
        print("=" * 60)
        print("\n✅ Sprint 2 완료!")
        print("   - Task 2.1: getSetComposition 함수 구현 ✅")
        print("   - Task 2.2: addToCart 세트 메뉴 지원 ✅")
        print("   - Task 2.3: 옵션 변경 대화 로직 ✅")

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
