import os
import json
from typing import Dict, List, Any
from openai import OpenAI
from dotenv import load_dotenv
from order_bot import BurgeriaOrderBot

load_dotenv()

class BurgeriaLLMBot:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.order_bot = BurgeriaOrderBot()
        self.system_prompt = self._create_system_prompt()
        
    def _create_system_prompt(self) -> str:
        return """
당신은 Burgeria(버거리아) 햄버거 매장의 친절한 직원입니다.

**역할과 규칙:**
1. 주문 접수만 담당합니다. 주문과 무관한 질문에는 정중히 거절하세요.
2. 메뉴에 없는 상품은 절대 추천하지 마세요.
3. 고객이 모호하게 말하면 findProduct로 검색 후 선택지를 제시하세요.
4. 가격은 항상 정확히 안내하세요.
5. 친절하지만 간결하게 응답하세요.

**주문 프로세스:**
1. 메뉴 검색 → 2. 옵션 확인 → 3. 장바구니 추가 → 4. 계속 주문 여부 → 5. 최종 결제

**거절해야 할 질문 예시:**
- 날씨, 뉴스, 일반 상식 문의
- 다른 매장 정보
- 요리법, 레시피
- 개인적인 상담

**사용 가능한 함수:**
- findProduct: 메뉴 검색
- addToCart: 장바구니 추가  
- getCartDetails: 장바구니 조회
- clearCart: 장바구니 비우기
- updateCartItem: 수량 변경
- processOrder: 최종 주문

항상 고객의 의도를 정확히 파악하여 적절한 함수를 호출하세요.
"""

    def _get_function_definitions(self) -> List[Dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "findProduct",
                    "description": "사용자가 모호하게 말한 메뉴명으로 상품을 검색합니다",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "검색할 메뉴명 (예: 양념감자, 불고기버거)"
                            },
                            "category": {
                                "type": "string",
                                "description": "선택적 카테고리 필터",
                                "enum": ["burger", "sides", "beverage", "set"]
                            },
                            "limit": {
                                "type": "integer",
                                "description": "검색 결과 제한 (기본값 5)"
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
                    "description": "상품을 장바구니에 추가합니다",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "사용자 세션 ID"
                            },
                            "product_id": {
                                "type": "string",
                                "description": "상품 ID (예: A00001, G00001)"
                            },
                            "quantity": {
                                "type": "integer",
                                "description": "주문 수량",
                                "default": 1
                            },
                            "order_type": {
                                "type": "string",
                                "description": "주문 타입",
                                "enum": ["single", "set"],
                                "default": "single"
                            },
                            "modifications": {
                                "type": "array",
                                "description": "옵션 변경사항",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "type": {
                                            "type": "string",
                                            "enum": ["add_topping", "change_component", "size_upgrade"]
                                        },
                                        "target_product_id": {"type": "string"},
                                        "new_product_id": {"type": "string"}
                                    }
                                }
                            },
                            "special_requests": {
                                "type": "string",
                                "description": "특별 요청사항"
                            }
                        },
                        "required": ["session_id", "product_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "getCartDetails",
                    "description": "현재 장바구니 내용을 조회합니다",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "사용자 세션 ID"
                            }
                        },
                        "required": ["session_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "clearCart",
                    "description": "장바구니를 비우거나 특정 항목을 제거합니다",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "사용자 세션 ID"
                            },
                            "cart_item_id": {
                                "type": "string",
                                "description": "제거할 특정 항목 ID (선택사항)"
                            },
                            "clear_all": {
                                "type": "boolean",
                                "description": "전체 삭제 여부",
                                "default": False
                            }
                        },
                        "required": ["session_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "updateCartItem",
                    "description": "장바구니 항목의 수량을 변경합니다",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"},
                            "cart_item_id": {"type": "string"},
                            "new_quantity": {"type": "integer"},
                            "action": {
                                "type": "string",
                                "enum": ["update_quantity"],
                                "default": "update_quantity"
                            }
                        },
                        "required": ["session_id", "cart_item_id", "new_quantity"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "processOrder",
                    "description": "최종 주문을 처리합니다",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"},
                            "customer_info": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "phone": {"type": "string"}
                                }
                            },
                            "order_type": {
                                "type": "string",
                                "enum": ["takeout", "dine_in"],
                                "default": "takeout"
                            }
                        },
                        "required": ["session_id"]
                    }
                }
            }
        ]
    
    def _execute_function(self, function_name: str, arguments: Dict) -> Dict[str, Any]:
        """Execute the called function and return result"""
        try:
            if function_name == "findProduct":
                return self.order_bot.findProduct(
                    query=arguments["query"],
                    category=arguments.get("category"),
                    limit=arguments.get("limit", 5)
                )
            
            elif function_name == "addToCart":
                return self.order_bot.addToCart(
                    session_id=arguments["session_id"],
                    product_id=arguments["product_id"],
                    quantity=arguments.get("quantity", 1),
                    order_type=arguments.get("order_type", "single"),
                    modifications=arguments.get("modifications", []),
                    special_requests=arguments.get("special_requests", "")
                )
            
            elif function_name == "getCartDetails":
                return self.order_bot.getCartDetails(arguments["session_id"])
            
            elif function_name == "clearCart":
                return self.order_bot.clearCart(
                    session_id=arguments["session_id"],
                    cart_item_id=arguments.get("cart_item_id"),
                    clear_all=bool(arguments.get("clear_all", False))
                )
            
            elif function_name == "updateCartItem":
                return self.order_bot.updateCartItem(
                    session_id=arguments["session_id"],
                    cart_item_id=arguments["cart_item_id"],
                    new_quantity=arguments["new_quantity"],
                    action=arguments.get("action", "update_quantity")
                )
            
            elif function_name == "processOrder":
                return self.order_bot.processOrder(
                    session_id=arguments["session_id"],
                    customer_info=arguments.get("customer_info"),
                    order_type=arguments.get("order_type", "takeout")
                )
            
            else:
                return {"success": False, "error": f"Unknown function: {function_name}"}
                
        except Exception as e:
            import traceback
            return {"success": False, "error": f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"}
    
    def chat(self, user_message: str, session_id: str, conversation_history: List[Dict] = None) -> str:
        """Process user message and return AI response"""
        if conversation_history is None:
            conversation_history = []
        
        # Build messages
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_message})
        
        try:
            # First API call
            response = self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=messages,
                tools=self._get_function_definitions(),
                tool_choice="auto"
            )
            
            response_message = response.choices[0].message
            
            # Check if function was called
            if response_message.tool_calls:
                # Add assistant message to conversation
                messages.append({
                    "role": "assistant",
                    "content": response_message.content,
                    "tool_calls": response_message.tool_calls
                })
                
                # Execute function calls
                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError as e:
                        return f"JSON 파싱 오류: {str(e)}, 원본: {tool_call.function.arguments}"
                    
                    # Add session_id if not provided (for functions that need it)
                    if function_name != "findProduct" and "session_id" not in arguments:
                        arguments["session_id"] = session_id
                    
                    function_result = self._execute_function(function_name, arguments)
                    
                    # Add function result to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(function_result, ensure_ascii=False)
                    })
                
                # Second API call with function results
                second_response = self.client.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=messages
                )
                
                return second_response.choices[0].message.content
            
            else:
                return response_message.content
                
        except Exception as e:
            return f"죄송합니다. 시스템 오류가 발생했습니다: {str(e)}"