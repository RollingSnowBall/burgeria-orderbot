# AI Function Calling 명세서

## 1. findProduct 함수

### 목적
사용자가 모호하게 말한 메뉴명을 기반으로 실제 메뉴 후보들을 찾아주는 함수

### 입력 (Input)
```json
{
  "function_name": "findProduct",
  "parameters": {
    "query": "string",           // 사용자가 말한 메뉴명 (예: "양념감자", "불고기버거", "콜라")
    "category": "string",        // 선택적 카테고리 필터 (예: "burger", "sides", "beverage")
    "limit": "number"            // 선택적 결과 제한 (기본값: 5)
  }
}
```

### 출력 (Output)
```json
{
  "success": true,
  "matches": [
    {
      "product_id": "B00003",
      "product_name": "양념감자 (어니언)",
      "product_type": "sides",
      "price": 2600,
      "description": "어니언 시즈닝을 뿌려먹는 포테이토",
      "stock_quantity": 2000,
      "match_score": 0.95
    },
    {
      "product_id": "B00004",
      "product_name": "양념감자 (칠리)",
      "product_type": "sides",
      "price": 2600,
      "description": "칠리 시즈닝을 뿌려먹는 포테이토",
      "stock_quantity": 2000,
      "match_score": 0.95
    }
  ],
  "total_found": 4
}
```

### 처리 로직
1. 키워드 기반 검색 (product_name에서 유사도 매칭)
2. 카테고리 필터링 (제공된 경우)
3. 재고량 체크 (stock_quantity > 0인 것만)
4. 매칭 점수별 정렬
5. limit 수만큼 반환

### 사용 예시
- 사용자: "양념감자 주세요"
- LLM이 findProduct 호출
- 4가지 양념감자 옵션 반환
- LLM이 사용자에게 "어떤 양념감자를 원하시나요? 어니언, 칠리, 치즈, 실비김치가 있습니다" 응답

---

## 2. addToCart 함수

### 목적
단품, 세트, 옵션 변경 등 모든 주문 케이스를 처리하여 장바구니에 추가하는 핵심 함수

### 입력 (Input)
```json
{
  "function_name": "addToCart",
  "parameters": {
    "session_id": "string",          // 사용자 세션 ID
    "product_id": "string",          // 주문할 상품 ID (예: "A00001", "G00001")
    "quantity": "number",            // 주문 수량 (기본값: 1)
    "order_type": "string",          // "single" | "set"
    "modifications": [               // 선택적 옵션 변경사항
      {
        "type": "add_topping",       // "add_topping" | "change_component" | "size_upgrade"
        "target_product_id": "string", // 변경 대상 상품 ID
        "new_product_id": "string"     // 새로운 상품 ID
      }
    ],
    "special_requests": "string"     // 선택적 특별 요청사항
  }
}
```

### 출력 (Output)
```json
{
  "success": true,
  "cart_item_id": "string",        // 생성된 장바구니 항목 ID
  "message": "string",             // 확인 메시지
  "item_details": {
    "product_name": "string",
    "base_price": 9000,
    "modifications": [
      {
        "description": "치즈토핑 추가",
        "price_change": 1000
      }
    ],
    "total_price": 10000,
    "quantity": 1
  },
  "price_breakdown": {
    "base_price": 9000,
    "modification_cost": 1000,
    "subtotal": 10000,
    "quantity": 1,
    "line_total": 10000
  }
}
```

### 처리 로직

#### A. 단품 주문 (order_type: "single")
1. product_id가 존재하는지 확인
2. 재고 확인 (stock_quantity >= quantity)
3. modifications 처리:
   - add_topping: 토핑 추가 (+1000원)
   - 각 modification의 가격 변경사항 계산
4. 최종 가격 계산 및 장바구니 추가

#### B. 세트 주문 (order_type: "set")
1. 세트 상품인지 확인 (product_type = "set")
2. Set_Items 테이블에서 구성품 조회
3. modifications 처리:
   - change_component: 사이드/음료 변경 (가격차이 계산)
   - size_upgrade: 라지사이즈 업그레이드 (+200원)
   - add_topping: 버거에 토핑 추가
4. 세트 할인 적용된 최종 가격 계산

### 사용 예시들

#### 예시 1: 단품 버거 + 토핑 추가
```json
{
  "product_id": "A00001",
  "quantity": 1,
  "order_type": "single",
  "modifications": [
    {
      "type": "add_topping",
      "target_product_id": "A00001",
      "new_product_id": "D00002"
    }
  ]
}
```

#### 예시 2: 세트 주문 + 음료 변경
```json
{
  "product_id": "G00001",
  "quantity": 1,
  "order_type": "set",
  "modifications": [
    {
      "type": "change_component",
      "target_product_id": "C00001",
      "new_product_id": "C00007"
    }
  ]
}
```

---

## 3. getCartDetails 함수

### 목적
현재 사용자의 장바구니 내용을 조회하여 주문 내역과 총 금액을 반환

### 입력 (Input)
```json
{
  "function_name": "getCartDetails",
  "parameters": {
    "session_id": "string"           // 사용자 세션 ID
  }
}
```

### 출력 (Output)
```json
{
  "success": true,
  "cart_items": [
    {
      "cart_item_id": "string",
      "product_name": "한우불고기버거 세트",
      "order_type": "set",
      "quantity": 1,
      "base_price": 10200,
      "modifications": [
        {
          "description": "음료 변경: 콜라 → 아이스티",
          "price_change": 300
        }
      ],
      "line_total": 10500,
      "special_requests": ""
    }
  ],
  "summary": {
    "total_items": 1,
    "total_quantity": 1,
    "subtotal": 10500,
    "tax": 0,
    "total_amount": 10500
  },
  "message": "장바구니에 1개의 상품이 있습니다."
}
```

---

## 4. clearCart 함수

### 목적
사용자의 장바구니를 완전히 비우거나 특정 항목만 제거

### 입력 (Input)
```json
{
  "function_name": "clearCart",
  "parameters": {
    "session_id": "string",          // 사용자 세션 ID
    "cart_item_id": "string",        // 선택적: 특정 항목만 제거할 경우
    "clear_all": "boolean"           // true: 전체 삭제, false: 특정 항목만 삭제
  }
}
```

### 출력 (Output)
```json
{
  "success": true,
  "message": "장바구니가 비워졌습니다.",
  "removed_items": 2,
  "remaining_items": 0
}
```

---

## 5. updateCartItem 함수

### 목적
장바구니에 있는 기존 항목의 수량이나 옵션을 수정

### 입력 (Input)
```json
{
  "function_name": "updateCartItem",
  "parameters": {
    "session_id": "string",
    "cart_item_id": "string",
    "new_quantity": "number",        // 선택적: 새로운 수량
    "modifications": [],             // 선택적: 새로운 옵션 변경사항
    "action": "string"               // "update_quantity" | "update_options"
  }
}
```

### 출력 (Output)
```json
{
  "success": true,
  "updated_item": {
    "cart_item_id": "string",
    "product_name": "string",
    "new_quantity": 2,
    "new_line_total": 21000
  },
  "message": "주문 수량이 2개로 변경되었습니다."
}
```

---

## 6. processOrder 함수

### 목적
장바구니의 모든 항목을 최종 주문으로 처리하고 주문 번호 생성

### 입력 (Input)
```json
{
  "function_name": "processOrder",
  "parameters": {
    "session_id": "string",
    "customer_info": {               // 선택적: 고객 정보
      "name": "string",
      "phone": "string"
    },
    "order_type": "string"           // "takeout" | "dine_in"
  }
}
```

### 출력 (Output)
```json
{
  "success": true,
  "order_id": "ORD_20250913_001",
  "estimated_time": 15,              // 예상 준비 시간 (분)
  "total_amount": 10500,
  "order_summary": {
    "items": [...],
    "total_quantity": 1
  },
  "message": "주문이 완료되었습니다. 주문번호: ORD_20250913_001, 예상 대기시간: 15분"
}
```
