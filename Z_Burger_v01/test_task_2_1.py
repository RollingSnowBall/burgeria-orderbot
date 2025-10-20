"""
Task 2.1 단위 테스트: getSetComposition 함수 검증
"""

import sys
import os
import io

# Windows 인코딩 문제 해결
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# db_functions 모듈 import를 위한 경로 설정
sys.path.insert(0, os.path.dirname(__file__))

from db_functions import getSetComposition, get_default_db_path


def test_getSetComposition_valid_set():
    """정상적인 세트 메뉴 조회 테스트"""
    print("\n=== Test 1: 정상 세트 메뉴 조회 (G00001 - 한우불고기버거 세트) ===")

    result = getSetComposition("G00001")

    print(f"Success: {result['success']}")
    print(f"Set ID: {result['set_product_id']}")
    print(f"Set Name: {result['set_name']}")
    print(f"Message: {result['message']}")
    print(f"구성품 개수: {len(result['items'])}")

    if result['items']:
        print("\n구성품 상세:")
        for item in result['items']:
            print(f"  - {item['product_name']} (ID: {item['product_id']}, "
                  f"타입: {item['product_type']}, 가격: {item['price']}원, 수량: {item['quantity']})")

    # 검증
    assert result['success'] == True, "조회가 실패했습니다."
    assert result['set_name'] == "한우불고기버거 세트", "세트명이 일치하지 않습니다."
    assert len(result['items']) == 3, f"구성품이 3개여야 하는데 {len(result['items'])}개입니다."

    # 구성품 ID 확인 (버거, 사이드, 음료)
    item_ids = [item['product_id'] for item in result['items']]
    assert 'A00001' in item_ids, "한우불고기버거가 구성품에 없습니다."
    assert 'B00001' in item_ids, "포테이토가 구성품에 없습니다."
    assert 'C00001' in item_ids, "콜라가 구성품에 없습니다."

    print("\n✅ Test 1 통과!")
    return True


def test_getSetComposition_invalid_id():
    """존재하지 않는 세트 ID 조회 테스트"""
    print("\n=== Test 2: 존재하지 않는 세트 ID (G99999) ===")

    result = getSetComposition("G99999")

    print(f"Success: {result['success']}")
    print(f"Message: {result['message']}")

    # 검증
    assert result['success'] == False, "존재하지 않는 ID는 실패해야 합니다."
    assert result['set_name'] is None, "세트명이 None이어야 합니다."
    assert len(result['items']) == 0, "구성품이 비어있어야 합니다."

    print("✅ Test 2 통과!")
    return True


def test_getSetComposition_non_set_product():
    """세트가 아닌 상품 조회 테스트"""
    print("\n=== Test 3: 세트가 아닌 상품 ID (A00001 - 단품 버거) ===")

    result = getSetComposition("A00001")

    print(f"Success: {result['success']}")
    print(f"Set Name: {result['set_name']}")
    print(f"Message: {result['message']}")

    # 검증
    assert result['success'] == False, "단품은 실패해야 합니다."
    assert result['set_name'] == "한우불고기버거", "상품명은 조회되어야 합니다."
    assert len(result['items']) == 0, "구성품이 비어있어야 합니다."
    assert "세트 메뉴가 아닙니다" in result['message'], "적절한 오류 메시지가 있어야 합니다."

    print("✅ Test 3 통과!")
    return True


def test_getSetComposition_multiple_sets():
    """여러 세트 메뉴 조회 테스트"""
    print("\n=== Test 4: 여러 세트 메뉴 조회 ===")

    test_sets = [
        ("G00001", "한우불고기버거 세트"),
        ("G00003", "리아 불고기버거 세트"),
        ("G00009", "클래식 치즈버거 세트")
    ]

    for set_id, expected_name in test_sets:
        result = getSetComposition(set_id)
        print(f"\n{set_id}: {result['set_name']} - 구성품 {len(result['items'])}개")

        assert result['success'] == True, f"{set_id} 조회 실패"
        assert result['set_name'] == expected_name, f"세트명 불일치: {result['set_name']}"
        assert len(result['items']) == 3, f"{set_id} 구성품이 3개가 아닙니다."

    print("\n✅ Test 4 통과!")
    return True


def main():
    """모든 테스트 실행"""
    print("=" * 60)
    print("Task 2.1 getSetComposition 함수 단위 테스트")
    print("=" * 60)

    db_path = get_default_db_path()
    print(f"DB 경로: {db_path}")

    try:
        test_getSetComposition_valid_set()
        test_getSetComposition_invalid_id()
        test_getSetComposition_non_set_product()
        test_getSetComposition_multiple_sets()

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
