# 🍔 Mr. Burger 개발 진행 현황

> 마지막 업데이트: 2025-10-03

## 📂 프로젝트 구조

```
burgeria-orderbot/
├── Z_Burger_v01/           # 현재 작업 중인 MVP 버전
│   ├── Mr_Burger.py        # 메인 챗봇 (OpenAI Function Calling)
│   └── db_functions.py     # DB 함수 (findProduct, addToCart)
├── SET.sql                 # DB 스키마 및 샘플 데이터
├── spec.md                 # 기능 명세서
└── plan.md                 # 스프린트 계획 및 진행 상태
```

## ✅ Sprint 1 완료 (MVP 기반 구축)

### 구현된 기능

**1. DB 스키마 (SET.sql)**
- `Products`, `MenuCategory`, `Set_Items`, `Cart`, `Orders`, `Order_Items`
- 67개 샘플 데이터 (버거 19, 사이드 15, 음료 16, 토핑 5, 세트 19)

**2. findProduct 함수 (db_functions.py)**
- SQL LIKE 기반 검색
- 카테고리 필터 지원
- 재고 확인 포함

**3. addToCart 함수 (db_functions.py)**
- 단품 메뉴 장바구니 추가
- 수량 처리 지원
- 세트 메뉴는 거부 (Task 2.2에서 구현 예정)

**4. OpenAI Function Calling (Mr_Burger.py)**
- findProduct, addToCart 자동 호출
- session_id 자동 주입
- 대화 기록 관리 (tool_calls 포함)

**5. 시스템 프롬프트**
- product_id 정확성 보장
- 수량 파싱 및 반영
- 주문 프로세스 가이드

### 테스트 완료 시나리오

```
고객: "김치 불고기 버거 하나요"
→ findProduct("김치 불고기 버거")
→ "6,500원입니다. 담아드릴까요?"
고객: "네"
→ addToCart(session_id, "A00004", quantity=1)
→ "장바구니에 담았습니다!"
```

```
고객: "한우불고기버거 3개 주세요"
→ findProduct("한우불고기버거")
→ "3개면 총 27,000원입니다. 담아드릴까요?"
고객: "네"
→ addToCart(session_id, "A00001", quantity=3)
→ "3개를 장바구니에 담았습니다!"
```

## 🔄 다음 단계: Sprint 2 (세트 메뉴 및 옵션 처리)

### Task 2.1: getSetComposition 함수 구현
- 세트 상품 ID → 기본 구성품 목록 반환
- 예: `G00001` → `['A00001', 'B00001', 'C00001']`

### Task 2.2: addToCart 세트 메뉴 지원
- `set_group_id`로 구성품 그룹화
- 모든 구성품을 Cart 테이블에 추가

### Task 2.3: 옵션 변경 대화 로직
- "한우불고기버거 세트에서 감자튀김을 양념감자로 바꿔줘"
- 카테고리 검증, 가격 차이 계산, 사용자 확인

## 🎯 핵심 파일

| 파일 | 역할 | 다음 작업 시 참고 사항 |
|-----|------|---------------------|
| `Z_Burger_v01/Mr_Burger.py` | 메인 챗봇 | Function calling 추가 시 여기 수정 |
| `Z_Burger_v01/db_functions.py` | DB 함수 | 새 함수 추가 시 여기 작성 |
| `SET.sql` | DB 스키마 | 테이블 구조 확인 |
| `spec.md` | 기능 명세 | 구현 내용 상세 확인 |
| `plan.md` | 진행 상황 | 다음 Task 확인 |

## 🗄️ DB 정보

- **경로**: `C:\data\BurgeriaDB.db`
- **주요 테이블**:
  - `Products`: 상품 정보 (product_id, product_name, product_type, price)
  - `Cart`: 장바구니 (cart_item_id, session_id, product_id, quantity, set_group_id)
  - `Set_Items`: 세트 구성품 (set_product_id, component_product_id, is_default)

## 🔧 주요 설정

- **OpenAI 모델**: `gpt-4o-mini`
- **Function Calling**: `tools` 배열에 함수 정의
- **Session 관리**: 프로그램 시작 시 UUID 생성

## 📝 작업 재개 시 체크리스트

1. ✅ `plan.md` 읽고 현재 Task 확인
2. ✅ `spec.md`에서 해당 Task 상세 내용 확인
3. ✅ `Z_Burger_v01/` 폴더에서 코드 작성
4. ✅ 테스트 후 `plan.md` 상태 업데이트
5. ✅ 완료 시 다음 Task로 이동
