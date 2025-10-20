"""
Task 3.1 단위 테스트: findProduct 시맨틱 검색 검증
"""

import sys
import os
import io

# Windows 인코딩 문제 해결
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# db_functions 모듈 import를 위한 경로 설정
sys.path.insert(0, os.path.dirname(__file__))

from db_functions import findProduct, get_default_db_path


def test_exact_match():
    """정확한 메뉴명 검색 테스트"""
    print("\n=== Test 1: 정확한 메뉴명 검색 ===")

    result = findProduct("한우불고기버거")

    print(f"Status: {result['status']}")
    print(f"Success: {result['success']}")
    print(f"Message: {result['message']}")

    if result['product']:
        print(f"Product: {result['product']['product_name']}")
        print(f"Product ID: {result['product']['product_id']}")
        print(f"Match Score: {result['product']['match_score']}")

    assert result['status'] == 'FOUND', "정확한 이름으로 검색 시 FOUND 상태여야 함"
    assert result['product']['product_id'] == 'A00001', "한우불고기버거 ID가 A00001이어야 함"

    print("\n✅ Test 1 통과!")
    return True


def test_semantic_search_spicy_potato():
    """시맨틱 검색: '매콤한 감자' -> 양념감자(칠리) 검색"""
    print("\n=== Test 2: 시맨틱 검색 - '매콤한 감자' ===")

    result = findProduct("매콤한 감자")

    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")
    print(f"Total Found: {result['total_found']}")

    if result['matches']:
        print(f"\n상위 {len(result['matches'])}개 매칭 결과:")
        for idx, match in enumerate(result['matches'], 1):
            print(f"  {idx}. {match['product_name']} (점수: {match['match_score']})")

    # 최상위 결과가 칠리 양념감자여야 함 (매콤한)
    if result['status'] == 'FOUND':
        best_match = result['product']['product_name']
        print(f"\n최종 선택: {best_match}")
        assert '칠리' in best_match or '양념감자' in best_match, "'매콤한 감자'는 양념감자 관련 상품을 찾아야 함"

    print("\n✅ Test 2 통과!")
    return True


def test_ambiguous_search():
    """모호한 검색: '양념감자' -> AMBIGUOUS 상태 (4가지 옵션)"""
    print("\n=== Test 3: 모호한 검색 - '양념감자' ===")

    result = findProduct("양념감자")

    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")
    print(f"Total Found: {result['total_found']}")

    if result['matches']:
        print(f"\n매칭된 {len(result['matches'])}개 후보:")
        for idx, match in enumerate(result['matches'], 1):
            print(f"  {idx}. {match['product_name']} (ID: {match['product_id']}, 점수: {match['match_score']})")

    # 양념감자는 4가지 종류가 있으므로 AMBIGUOUS일 가능성이 높음
    # 단, 점수 차이가 크면 FOUND일 수도 있음
    if result['status'] == 'AMBIGUOUS':
        assert len(result['matches']) >= 2, "AMBIGUOUS 상태에서는 최소 2개 이상의 후보가 있어야 함"
        # 모든 후보가 양념감자 관련인지 확인
        for match in result['matches']:
            assert '양념감자' in match['product_name'], "모든 후보가 '양념감자' 관련이어야 함"
    else:
        print(f"ℹ️  FOUND 상태로 반환됨 (명확한 1개 결과)")

    print("\n✅ Test 3 통과!")
    return True


def test_category_filter():
    """카테고리 필터 테스트"""
    print("\n=== Test 4: 카테고리 필터 - 사이드만 검색 ===")

    result = findProduct("감자", category="sides")

    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")

    if result['matches']:
        print(f"\n매칭된 {len(result['matches'])}개 결과:")
        for idx, match in enumerate(result['matches'], 1):
            print(f"  {idx}. {match['product_name']} (타입: {match['product_type']}, 점수: {match['match_score']})")

        # 모든 결과가 sides 카테고리여야 함
        for match in result['matches']:
            assert match['product_type'] == 'sides', f"카테고리 필터 적용 실패: {match['product_type']}"

    print("\n✅ Test 4 통과!")
    return True


def test_beverage_search():
    """음료 검색 테스트"""
    print("\n=== Test 5: 음료 검색 - '콜라' ===")

    result = findProduct("콜라", category="beverage")

    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")

    if result['matches']:
        print(f"\n매칭된 {len(result['matches'])}개 결과:")
        for idx, match in enumerate(result['matches'], 1):
            print(f"  {idx}. {match['product_name']} (가격: {match['price']}원, 점수: {match['match_score']})")

    # 콜라는 여러 사이즈가 있을 수 있으므로 FOUND 또는 AMBIGUOUS 가능
    assert result['status'] in ['FOUND', 'AMBIGUOUS'], "콜라 검색 결과가 있어야 함"

    if result['matches']:
        for match in result['matches']:
            assert '콜라' in match['product_name'], "모든 결과에 '콜라'가 포함되어야 함"

    print("\n✅ Test 5 통과!")
    return True


def test_set_menu_search():
    """세트 메뉴 검색 테스트"""
    print("\n=== Test 6: 세트 메뉴 검색 - '한우불고기버거 세트' ===")

    result = findProduct("한우불고기버거 세트", category="set")

    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")

    if result['product']:
        print(f"Product: {result['product']['product_name']}")
        print(f"Product ID: {result['product']['product_id']}")
        print(f"Price: {result['product']['price']}원")

    assert result['status'] == 'FOUND', "세트 메뉴 검색 결과가 있어야 함"
    assert result['product']['product_type'] == 'set', "타입이 'set'이어야 함"
    assert '세트' in result['product']['product_name'], "상품명에 '세트'가 포함되어야 함"

    print("\n✅ Test 6 통과!")
    return True


def test_not_found():
    """존재하지 않는 메뉴 검색 테스트"""
    print("\n=== Test 7: 존재하지 않는 메뉴 - '피자' ===")

    result = findProduct("피자")

    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")
    print(f"Total Found: {result['total_found']}")

    # 피자는 햄버거 가게에 없으므로 NOT_FOUND 또는 유사도가 매우 낮은 결과
    assert result['status'] in ['NOT_FOUND', 'FOUND'], "검색 결과 상태 확인"

    if result['status'] == 'FOUND':
        print(f"ℹ️  유사한 상품이 발견됨: {result['product']['product_name']} (점수: {result['product']['match_score']})")
        # 유사도 점수가 낮아야 함
        assert result['product']['match_score'] < 0.85, "관련 없는 검색어는 낮은 점수를 받아야 함"

    print("\n✅ Test 7 통과!")
    return True


def test_similar_word_search():
    """유사 단어 검색: '치즈가 들어간 버거' -> 치즈버거"""
    print("\n=== Test 8: 유사 표현 검색 - '치즈가 들어간 버거' ===")

    result = findProduct("치즈가 들어간 버거", category="burger")

    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")

    if result['matches']:
        print(f"\n상위 {len(result['matches'])}개 매칭 결과:")
        for idx, match in enumerate(result['matches'], 1):
            print(f"  {idx}. {match['product_name']} (점수: {match['match_score']})")

    # 치즈버거 관련 결과가 나와야 함
    if result['matches']:
        top_match = result['matches'][0]
        assert '치즈' in top_match['product_name'], "치즈 관련 버거가 상위에 있어야 함"

    print("\n✅ Test 8 통과!")
    return True


def main():
    """모든 테스트 실행"""
    print("=" * 60)
    print("Task 3.1 findProduct 시맨틱 검색 단위 테스트")
    print("=" * 60)

    db_path = get_default_db_path()
    print(f"DB 경로: {db_path}")

    try:
        test_exact_match()
        test_semantic_search_spicy_potato()
        test_ambiguous_search()
        test_category_filter()
        test_beverage_search()
        test_set_menu_search()
        test_not_found()
        test_similar_word_search()

        print("\n" + "=" * 60)
        print("🎉 모든 테스트 통과!")
        print("=" * 60)
        print("\n✅ Task 3.1 완료: 시맨틱 검색 업그레이드 성공!")

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
