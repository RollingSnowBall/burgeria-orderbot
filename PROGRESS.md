# 🍔 Mr. Burger 개발 진행 현황

> 마지막 업데이트: 2025-10-26

## 📂 프로젝트 구조

```
burgeria-orderbot/
├── Z_Burger_v01/                      # 현재 작업 중인 MVP 버전
│   ├── Mr_Burger.py                   # 메인 챗봇 (OpenAI Function Calling)
│   ├── db_functions.py                # DB 함수 (시맨틱 검색 + 세트 교체 포함)
│   ├── setup_embeddings.py            # 임베딩 생성 스크립트
│   ├── test_task_2_*.py               # Sprint 2 테스트 파일
│   ├── test_task_3_*.py               # Sprint 3 테스트 파일
│   ├── test_task_4_1.py               # Sprint 4 Task 4.1 테스트
│   ├── test_scenario_sprint2.md       # Sprint 2 시나리오
│   ├── test_scenario_task_3_2.md      # Task 3.2 시나리오
│   ├── test_scenario_task_3_3.md      # Task 3.3 시나리오
│   ├── test_scenario_task_3_4.md      # Task 3.4 시나리오 ⭐ NEW
│   └── test_scenario_task_4_1.md      # Task 4.1 시나리오
├── SET.sql                            # DB 스키마 및 샘플 데이터
├── spec.md                            # 기능 명세서 (로드맵)
├── plan.md                            # 스프린트 계획 및 진행 상태
└── PROGRESS.md                        # 이 파일 (진행 현황)
```

---

## ✅ Sprint 1 완료 (MVP 기반 구축)

### 구현된 기능

**1. DB 스키마 (SET.sql)**
- `Products`, `MenuCategory`, `Set_Items`, `Cart`, `Orders`, `Order_Items`
- 74개 샘플 데이터 (버거 19, 사이드 15, 음료 16, 토핑 5, 세트 19)
- ✨ **NEW**: `embedding` 컬럼 추가 (시맨틱 검색용)

**2. findProduct 함수 (db_functions.py)**
- ~~SQL LIKE 기반 검색~~ → ✨ **임베딩 기반 시맨틱 검색으로 업그레이드**
- OpenAI `text-embedding-3-small` 모델 사용
- 코사인 유사도 계산
- **상태 구분**: `FOUND`, `AMBIGUOUS`, `NOT_FOUND`, `ERROR`
- 카테고리 필터 지원
- 재고 확인 포함

**3. addToCart 함수 (db_functions.py)**
- 단품 메뉴 장바구니 추가
- ✨ **세트 메뉴 지원** (Sprint 2에서 추가됨)
- 수량 처리 지원
- `set_group_id`로 세트 구성품 그룹화
- `special_requests` 필드로 옵션 변경사항 기록

**4. getSetComposition 함수 (db_functions.py)**
- ✨ **Sprint 2에서 추가됨**
- 세트 상품 ID → 기본 구성품 목록 반환
- 카테고리 검증 지원

**5. OpenAI Function Calling (Mr_Burger.py)**
- findProduct, addToCart, getSetComposition 자동 호출
- session_id 자동 주입
- 대화 기록 관리 (tool_calls 포함)
- ✨ **AMBIGUOUS 상태 처리 로직 추가** (Sprint 3에서 추가됨)

**6. 시스템 프롬프트**
- product_id 정확성 보장
- 수량 파싱 및 반영
- 주문 프로세스 가이드
- ✨ **세트 옵션 변경 프로세스** (Sprint 2에서 추가됨)
- ✨ **모호한 검색 시 선택지 제시 로직** (Sprint 3에서 추가됨)

---

## ✅ Sprint 2 완료 (세트 메뉴 및 대화형 검증)

### Task 2.1: getSetComposition 함수 ✅
- 세트 상품 ID로 기본 구성품 조회
- 예: `G00001` → 한우불고기버거, 포테이토, 콜라
- 단위 테스트 통과 (test_task_2_1.py)

### Task 2.2: addToCart 세트 메뉴 지원 ✅
- `set_group_id`로 구성품 그룹화
- 모든 구성품을 Cart 테이블에 추가
- 세트 수량 처리 (각 구성품 수량 동일하게 증가)
- 통합 테스트 통과 (test_task_2_2.py)

### Task 2.3: 옵션 변경 대화 로직 ✅
- 세트 구성품 변경 시나리오 지원
- 가격 차이 계산 및 고객 확인
- 카테고리 검증 (사이드→사이드, 음료→음료만 가능)
- `special_requests` 필드에 변경사항 기록
- 통합 테스트 통과 (test_task_2_3_integration.py)

### 테스트 완료 시나리오

```
고객: "한우불고기버거 세트 주세요"
→ findProduct("한우불고기버거 세트") → G00001
→ "10,200원입니다. 담아드릴까요?"
고객: "네"
→ addToCart(session_id, "G00001", quantity=1)
→ 장바구니에 3개 항목 추가 (버거, 사이드, 음료)
```

```
고객: "한우불고기버거 세트에서 감자튀김을 양념감자(칠리)로 바꿔주세요"
→ getSetComposition("G00001") → 포테이토 2000원 확인
→ findProduct("양념감자 칠리") → 2600원
→ 추가금 계산: 600원
→ "양념감자(칠리)로 변경하시면 600원 추가됩니다. 변경하시겠습니까?"
고객: "네"
→ addToCart(session_id, "G00001", special_requests="포테이토→양념감자(칠리)")
```

---

## 🔄 Sprint 3 진행 중 (검색 고도화 및 UX 개선)

### Task 3.1: findProduct 시맨틱 검색 업그레이드 ✅

**구현 내용:**
1. **임베딩 시스템 구축**
   - Products 테이블에 `embedding` 컬럼 추가
   - OpenAI `text-embedding-3-small` 모델 사용
   - 74개 전체 상품 임베딩 생성 및 저장

2. **시맨틱 검색 함수**
   - 쿼리 임베딩 생성
   - 코사인 유사도 계산
   - 유사도 임계값: 0.50
   - 모호성 임계값: 0.08

3. **상태 반환 로직**
   - `FOUND`: 명확한 1개 결과
   - `AMBIGUOUS`: 여러 유사한 결과 (점수 차이 < 0.08)
   - `NOT_FOUND`: 매칭되는 상품 없음
   - `ERROR`: 오류 발생

**테스트 결과:**
- ✅ 정확한 메뉴명 검색
- ✅ 의미 기반 검색 ("매콤한 감자" → NOT_FOUND, 임계값 조정 필요)
- ✅ 모호한 검색 ("양념감자" → AMBIGUOUS, 4개 후보)
- ✅ 카테고리 필터
- ✅ 세트 메뉴 검색

### Task 3.2: 모호성 처리 대화 로직 ✅

**구현 내용:**
1. **시스템 프롬프트 업데이트**
   - AMBIGUOUS 상태 처리 로직 추가
   - 선택지 제시 규칙 명확화
   - 번호/텍스트 선택 모두 지원

2. **임계값 조정**
   - `similarity_threshold`: 0.60 → 0.50
   - `ambiguity_threshold`: 0.02 → 0.08

**예시:**
```
고객: "양념감자 주세요"
봇: "양념감자는 4가지 맛이 있습니다. 어떤 것으로 드릴까요?
     1. 양념감자 (어니언) - 2,600원
     2. 양념감자 (칠리) - 2,600원
     3. 양념감자 (치즈) - 2,600원
     4. 양념감자 (실비김치) - 2,600원"

고객: "칠리로 주세요" (또는 "2번")
봇: "양념감자 (칠리) 2,600원입니다. 장바구니에 담아드릴까요?"
```

**테스트 시나리오 문서 작성:**
- test_scenario_task_3_2.md (5개 시나리오)
- 실제 챗봇 테스트 진행됨 (일부 수정 필요)

### Task 3.3: 장바구니 관리 함수 ✅ 완료

**구현 내용:**
1. **getCartDetails(session_id)**
   - 장바구니 전체 조회
   - 상품명, 수량, 가격, 세트 그룹 정보 반환
   - 총 금액 자동 계산

2. **updateCartItem(cart_item_id, quantity)**
   - 장바구니 항목의 수량 변경
   - quantity=0이면 삭제 처리
   - line_total 자동 재계산

3. **clearCart(session_id)**
   - 해당 세션의 장바구니 전체 비우기
   - 삭제된 항목 수 반환

**테스트 결과:**
- ✅ 단위 테스트 8/8 통과 (test_task_3_3.py)
  - 빈 장바구니 조회
  - 단품 장바구니 조회
  - 세트 메뉴 장바구니 조회
  - 수량 변경
  - 항목 삭제 (수량 0)
  - 존재하지 않는 항목 처리
  - 장바구니 비우기
  - 이미 비어있는 장바구니 처리

**테스트 시나리오 문서 작성:**
- test_scenario_task_3_3.md (8개 시나리오)

### Task 3.4: updateSetItem 함수 (세트 구성품 교체) ✅ 완료

**구현 내용:**
1. **getSetMenusInCart(session_id, set_product_id) 헬퍼 함수**
   - 장바구니의 모든 세트 메뉴 조회
   - set_product_id로 특정 세트만 필터링 가능
   - 각 세트의 구성품, 가격, set_group_id 반환
   - 세트 상품 ID 자동 식별 (Set_Items 테이블과 매칭)

2. **updateSetItem(session_id, old_product_id, new_product_id, set_group_id) 함수**
   - **자동 선택 모드** (set_group_id 미제공 + 1개 세트만 있는 경우)
     - 세트를 자동으로 감지하여 교체
   - **수동 선택 모드** (set_group_id 미제공 + 여러 세트 있는 경우)
     - `MULTIPLE_SETS` 상태 반환
     - 사용자가 세트 선택 후 set_group_id 지정하여 재호출
   - **직접 지정 모드** (set_group_id 제공)
     - 해당 세트의 구성품만 교체
   - 가격 차이 자동 계산 및 안내 (추가/할인)

**테스트 결과:**
- ✅ 단위 테스트 8/8 통과 (test_task_3_4.py)
  - 단일 세트 자동 교체
  - 여러 세트 중 수동 선택
  - 교체 대상 상품이 없는 경우
  - 새 상품 ID가 유효하지 않은 경우
  - 가격이 낮아지는 교체 (할인)
  - 유효하지 않은 set_group_id
  - getSetMenusInCart 헬퍼 함수
  - 특정 세트 상품 필터링

**테스트 시나리오 문서 작성:**
- test_scenario_task_3_4.md (8개 시나리오)

**핵심 기술:**
- 세트 상품 ID 역추적: 장바구니의 구성품을 분석하여 원본 세트 상품(G00001 등) 자동 식별
- Best-match 알고리즘: 구성품 개수와 일치도를 기반으로 가장 적합한 세트 찾기
- 가격 차이 계산: 기존 상품과 새 상품의 가격 차이를 자동 계산하여 사용자에게 안내
- 장바구니 조회, 수량 변경, 삭제, 비우기 등 전체 프로세스

---

## 🔄 Sprint 4 진행 중 (주문 완료 및 시스템 안정화)

### Task 4.1: processOrder 함수 구현 ✅ 완료

**구현 내용:**
1. **processOrder(session_id, customer_name, customer_phone, order_type)**
   - 장바구니 조회 및 검증
   - Orders 테이블에 주문 생성
   - Order_Items 테이블에 주문 항목 저장
   - 장바구니 자동 비우기
   - 주문 번호 자동 생성 (날짜별 증가)

**기능:**
- 주문 ID 자동 생성 (ORD_XXXXXXXX)
- 주문 번호 날짜별 자동 증가
- 고객 정보 저장 (선택사항)
- 주문 유형 지정 (takeout, delivery, dine-in)
- 주문 상태 'pending'으로 초기화
- 예상 소요 시간 15분 설정

**테스트 결과:**
- ✅ 단위 테스트 5/5 통과 (test_task_4_1.py)
  - 기본 주문 생성
  - 세트 메뉴 주문
  - 빈 장바구니 주문 시도
  - 여러 상품 혼합 주문
  - 주문 번호 증가 확인

**테스트 시나리오 문서 작성:**
- test_scenario_task_4_1.md (8개 시나리오)
- 주문 생성, 고객 정보, DB 검증 등 전체 프로세스

---

## 📊 전체 진행 현황

| Sprint | 상태 | 완료율 | 비고 |
|--------|------|--------|------|
| Sprint 1 (MVP) | ✅ 완료 | 5/6 | 리뷰 제외 |
| Sprint 2 (세트 메뉴) | ✅ 완료 | 3/4 | 리뷰 제외, 테스트 모두 통과 |
| Sprint 3 (검색 고도화) | ✅ 완료 | 3/4 | 리뷰 제외, 장바구니 관리 완료 |
| Sprint 4 (주문 완료) | 🔄 진행 중 | 1/4 | Task 4.1 완료 |

**총 진행률: 12/18 (66.7%)**

---

## 🎯 핵심 파일

| 파일 | 역할 | 최근 업데이트 |
|-----|------|--------------|
| `Z_Burger_v01/Mr_Burger.py` | 메인 챗봇 | Task 3.2 (AMBIGUOUS 처리 로직) |
| `Z_Burger_v01/db_functions.py` | DB 함수 | Task 4.1 (processOrder 함수 추가) |
| `Z_Burger_v01/setup_embeddings.py` | 임베딩 생성 | Task 3.1에서 추가 |
| `Z_Burger_v01/test_task_3_3.py` | Task 3.3 테스트 | Task 3.3에서 추가 |
| `Z_Burger_v01/test_task_4_1.py` | Task 4.1 테스트 | Task 4.1에서 추가 |
| `SET.sql` | DB 스키마 | embedding 컬럼 추가 |
| `spec.md` | 기능 명세 | - |
| `plan.md` | 진행 상황 | 2025-10-26 업데이트 |

---

## 🗄️ DB 정보

- **경로**: `C:\data\BurgeriaDB.db`
- **주요 테이블**:
  - `Products`: 상품 정보 (product_id, product_name, product_type, price, **embedding**)
  - `Cart`: 장바구니 (cart_item_id, session_id, product_id, quantity, set_group_id)
  - `Set_Items`: 세트 구성품 (set_product_id, component_product_id, is_default)
  - `Orders`: 주문 정보 (order_id, session_id, total_amount, order_type, customer_name, status) - **Task 4.1에서 사용 중**
  - `Order_Items`: 주문 항목 (order_item_id, order_id, product_id, quantity, set_group_id) - **Task 4.1에서 사용 중**

---

## 🔧 주요 설정

- **OpenAI 모델**: `gpt-4o-mini`
- **임베딩 모델**: `text-embedding-3-small`
- **Function Calling**: `tools` 배열에 함수 정의
- **Session 관리**: 프로그램 시작 시 UUID 생성
- **검색 임계값**:
  - `similarity_threshold`: 0.50
  - `ambiguity_threshold`: 0.08

---

## 🚀 다음 작업 (Sprint 4 계속)

### Task 4.2: 시스템 전반 오류 처리 및 로깅 적용
- 재고 부족 처리
- DB 트랜잭션 실패 시 롤백
- 모든 함수 에러 핸들링 강화
- 로그 파일 생성 및 관리

### Task 4.3: 통합 테스트 및 버그 수정
- E2E 테스트 작성
- 전체 기능 회귀 테스트
- 성능 최적화
- 최종 문서화

---

## 📝 작업 재개 시 체크리스트

1. ✅ `plan.md` 읽고 현재 Task 확인
2. ✅ `spec.md`에서 해당 Task 상세 내용 확인
3. ✅ `Z_Burger_v01/` 폴더에서 코드 작성
4. ✅ 테스트 후 `plan.md` 상태 업데이트
5. ✅ 완료 시 `PROGRESS.md` 업데이트
6. ✅ 완료 시 다음 Task로 이동

---

## 🎯 다음 작업 (빠른 재개 가이드)

### 현재 상태 (2025-10-26 기준)
- ✅ **Sprint 3 완료**: 시맨틱 검색, 모호성 처리, 장바구니 관리, 세트 구성품 교체 모두 구현됨
- ✅ **Sprint 4 Task 4.1 완료**: processOrder 함수로 주문 생성 기능 완료
- 🔄 **Sprint 4 진행 중**: 1/4 완료 (리뷰 제외)

### 🆕 오늘 완료한 작업 (2025-10-26)
**Task 3.4: 세트 구성품 교체 기능 구현**
- ✅ `getSetMenusInCart()` 헬퍼 함수 구현 (db_functions.py:878-1056)
- ✅ `updateSetItem()` 메인 함수 구현 (db_functions.py:1059-1337)
- ✅ 단위 테스트 8개 작성 및 통과 (test_task_3_4.py)
- ✅ 통합 테스트 시나리오 8개 작성 (test_scenario_task_3_4.md)
- ✅ 문서 업데이트 (plan.md, PROGRESS.md)

**핵심 구현 내용:**
- 자동 선택: 1개 세트만 있으면 자동 교체
- 수동 선택: 여러 세트가 있으면 사용자 선택 요청
- 세트 역추적: 장바구니 구성품으로 원본 세트 상품 ID 자동 식별
- 가격 차이 계산: 추가/할인 금액 자동 계산 및 안내

### 다음 단계: Sprint 4 완료하기

**Option 1: Task 4.2 - 시스템 전반 오류 처리 및 로깅** (권장, 10시간 예상)
- 재고 부족 시 주문/교체 제한 로직
- DB 트랜잭션 실패 시 롤백 처리
- 모든 함수에 try-except 강화
- 로그 파일 생성 및 오류 추적 시스템

**Option 2: Task 4.3 - 통합 테스트 및 버그 수정** (8시간 예상)
- 전체 주문 프로세스 E2E 테스트 작성
- 세트 교체 → 주문 완료 통합 시나리오
- 버그 수정 및 성능 최적화
- 최종 문서화

### 재개 시 체크리스트
1. ✅ `plan.md` 확인: Sprint 4 현황 파악
2. ✅ `db_functions.py` 확인: 구현된 함수 목록
   - findProduct (시맨틱 검색)
   - addToCart (단품 + 세트)
   - getSetComposition
   - getCartDetails, updateCartItem, clearCart
   - **getSetMenusInCart, updateSetItem** ⭐ 최신 추가
   - processOrder
3. ✅ 테스트 파일 확인: `test_task_*.py`
4. ✅ 다음 Task 시작

---

## 🐛 알려진 이슈 및 TODO

### Task 3.3 관련
- [ ] 세트 메뉴 수량 변경 시 모든 구성품 일괄 변경 로직 필요 (현재는 개별 항목만 변경)
- [ ] 세트 할인 가격 분배 로직 검토 (현재는 구성품 개별 가격 합계로 저장)

### Task 3.2 관련
- [ ] 모호성 처리 로직 실제 챗봇 테스트에서 일부 수정 필요
- [ ] 번호 선택 시 인덱싱 로직 검증 필요

### 일반
- [ ] 임베딩 업데이트 자동화 (새 상품 추가 시)
- [ ] 성능 최적화 (임베딩 캐싱)
- [ ] 오프라인 모드 지원 (SequenceMatcher fallback)

---

## 📈 개발 타임라인

- **2025-10-03**: Sprint 1 완료 (MVP)
- **2025-10-20**: Sprint 2 완료 (세트 메뉴)
- **2025-10-20**: Sprint 3 Task 3.1, 3.2 완료 (시맨틱 검색 + 모호성 처리)
- **2025-10-26**: Sprint 3 Task 3.3 완료 (장바구니 관리 함수)
- **2025-10-26**: Sprint 3 Task 3.4 완료 (세트 구성품 교체 함수) ⭐ NEW
- **2025-10-26**: Sprint 4 Task 4.1 완료 (주문 생성 함수)
- **Next**: Task 4.2 (오류 처리 및 로깅) → Task 4.3 (통합 테스트)
