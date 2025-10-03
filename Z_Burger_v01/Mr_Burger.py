"""
Mr. Burger - 햄버거 주문 챗봇
CMD 기반 OpenAI 연동 대화형 주문 시스템
"""

import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from db_functions import findProduct, addToCart

# 환경변수 로드
load_dotenv()

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Function calling 정의
tools = [
    {
        "type": "function",
        "function": {
            "name": "findProduct",
            "description": "메뉴 검색 함수. 사용자가 메뉴를 주문하거나 찾을 때 사용합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "검색할 메뉴명 (예: 한우불고기버거, 콜라)"
                    },
                    "category": {
                        "type": "string",
                        "description": "카테고리 필터 (선택사항)",
                        "enum": ["burger", "sides", "beverage", "set"]
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "addToCart",
            "description": "단품 메뉴를 장바구니에 추가합니다. 세트 메뉴는 아직 지원하지 않습니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "사용자 세션 ID"
                    },
                    "product_id": {
                        "type": "string",
                        "description": "상품 ID (예: A00001)"
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "주문 수량 (기본값: 1)",
                        "default": 1
                    },
                    "special_requests": {
                        "type": "string",
                        "description": "특별 요청사항 (선택사항)",
                        "default": ""
                    }
                },
                "required": ["session_id", "product_id"]
            }
        }
    }
]

def execute_function(function_name: str, arguments: dict) -> dict:
    """
    함수 실행

    Args:
        function_name: 함수 이름
        arguments: 함수 인자

    Returns:
        함수 실행 결과
    """
    if function_name == "findProduct":
        return findProduct(
            query=arguments["query"],
            category=arguments.get("category")
        )
    elif function_name == "addToCart":
        return addToCart(
            session_id=arguments["session_id"],
            product_id=arguments["product_id"],
            quantity=arguments.get("quantity", 1),
            special_requests=arguments.get("special_requests", "")
        )
    else:
        return {"success": False, "error": f"Unknown function: {function_name}"}

def chat_with_llm(user_message: str, conversation_history: list, session_id: str = None) -> tuple:
    """
    OpenAI LLM과 대화 (Function Calling 지원)

    Args:
        user_message: 사용자 메시지
        conversation_history: 대화 기록
        session_id: 세션 ID (addToCart 함수에 필요)

    Returns:
        (LLM 응답, 업데이트된 대화 기록)
    """
    # 시스템 프롬프트
    system_prompt = """당신은 Burgeria(버거리아) 햄버거 매장의 친절한 직원입니다.

    **중요 규칙:**
    - addToCart를 호출할 때는 **반드시** findProduct 결과에서 받은 product_id를 **정확히 그대로** 사용하세요
    - product_id를 임의로 추측하거나 변경하지 마세요
    - findProduct 결과의 product 객체에 있는 product_id 값을 그대로 복사해서 사용하세요
    - 고객이 수량을 명시하면 (예: "2개", "3개") addToCart의 quantity 파라미터에 정확히 반영하세요
    - 수량 언급이 없으면 기본값 1개로 처리하세요

    **주문 프로세스:**
    1. 고객이 메뉴를 요청하면 findProduct로 검색
    2. findProduct 결과에서 product_id, product_name, price를 확인
    3. 고객에게 가격과 정보를 안내 (수량이 있으면 총 금액 계산해서 알려주기)
    4. 고객이 주문을 확정하면 **findProduct에서 받은 정확한 product_id**와 **수량**을 사용하여 addToCart 호출

    **예시 1 (수량 없음):**
    고객: "김치 불고기 버거 주세요"
    → findProduct("김치 불고기 버거") 호출
    → 결과: {"product": {"product_id": "A00004", "product_name": "김치 불고기 버거", "price": 6500}}
    → "네, 김치 불고기 버거가 6,500원입니다. 장바구니에 담아드릴까요?"
    고객: "네"
    → addToCart(session_id, "A00004", quantity=1) 호출
    → "김치 불고기 버거 1개를 장바구니에 담았습니다!"

    **예시 2 (수량 있음):**
    고객: "한우불고기버거 3개 주세요"
    → findProduct("한우불고기버거") 호출
    → 결과: {"product": {"product_id": "A00001", "product_name": "한우불고기버거", "price": 9000}}
    → "네, 한우불고기버거 3개면 총 27,000원입니다. 장바구니에 담아드릴까요?"
    고객: "네"
    → addToCart(session_id, "A00001", quantity=3) 호출
    → "한우불고기버거 3개를 장바구니에 담았습니다!"
    """

    # 메시지 구성
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_message})

    try:
        # 첫 번째 API 호출 (Function Calling)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )

        response_message = response.choices[0].message

        # 새로운 메시지를 저장할 리스트 (대화 기록 업데이트용)
        new_messages = []

        # Function call이 있는 경우
        if response_message.tool_calls:
            # assistant의 응답 추가 (대화 기록용)
            assistant_message = {
                "role": "assistant",
                "content": response_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in response_message.tool_calls
                ]
            }
            messages.append(assistant_message)
            new_messages.append(assistant_message)

            # 각 함수 호출 실행
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)

                # addToCart 함수 호출 시 session_id 자동 주입
                if function_name == "addToCart" and session_id:
                    arguments["session_id"] = session_id

                print(f"[DEBUG] 함수 호출: {function_name}({arguments})")

                # 함수 실행
                function_result = execute_function(function_name, arguments)

                # 함수 결과를 메시지에 추가
                tool_message = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(function_result, ensure_ascii=False)
                }
                messages.append(tool_message)
                new_messages.append(tool_message)

            # 두 번째 API 호출 (함수 결과를 바탕으로 응답 생성)
            second_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages
            )

            final_message = {
                "role": "assistant",
                "content": second_response.choices[0].message.content
            }
            new_messages.append(final_message)

            return second_response.choices[0].message.content, new_messages

        else:
            # Function call이 없으면 바로 응답 반환
            assistant_message = {
                "role": "assistant",
                "content": response_message.content
            }
            return response_message.content, [assistant_message]

    except Exception as e:
        error_message = {
            "role": "assistant",
            "content": f"오류가 발생했습니다: {str(e)}"
        }
        return f"오류가 발생했습니다: {str(e)}", [error_message]

def main():
    """메인 실행 함수"""
    print("\n" + "="*50)
    print("🍔 Mr. Burger 주문 시스템에 오신 것을 환영합니다!")
    print("="*50)
    print("종료하려면 'exit'를 입력하세요.\n")
    print("[DEBUG MODE] 'search:메뉴명' 형식으로 검색 테스트 가능\n")

    # 세션 ID 생성 (실제로는 사용자별로 생성해야 함)
    import uuid
    session_id = f"SESSION_{uuid.uuid4().hex[:8].upper()}"
    print(f"세션 ID: {session_id}\n")

    # 대화 기록 저장
    conversation_history = []

    while True:
        # 사용자 입력
        user_input = input("고객님> ").strip()

        if not user_input:
            continue

        if user_input.lower() == 'exit':
            print("\n감사합니다. 좋은 하루 되세요! 👋\n")
            break

        # DEBUG: findProduct 함수 테스트
        if user_input.lower().startswith('search:'):
            query = user_input[7:].strip()
            result = findProduct(query)
            print(f"\n[검색 결과]")
            print(f"상태: {result['status']}")
            print(f"메시지: {result['message']}")
            if result['product']:
                print(f"상품 정보: {result['product']}")
            print()
            continue

        # LLM 응답 받기 (session_id를 conversation_history에 포함하여 전달)
        # addToCart 함수 호출 시 session_id가 필요하므로 미리 설정
        response, new_messages = chat_with_llm(user_input, conversation_history, session_id)

        # 대화 기록에 추가
        conversation_history.append({"role": "user", "content": user_input})
        # Function calling 결과를 포함한 모든 메시지 추가
        conversation_history.extend(new_messages)

        # 응답 출력
        print(f"Mr.Burger> {response}\n")

if __name__ == "__main__":
    main()
