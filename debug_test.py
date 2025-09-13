from llm_integration import BurgeriaLLMBot
from order_bot import BurgeriaOrderBot  
import traceback
import json
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

def debug_openai_response():
    """OpenAI 응답을 직접 테스트해보기"""
    try:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "당신은 햄버거 매장 직원입니다. 간단히 인사해주세요."},
                {"role": "user", "content": "안녕하세요"}
            ]
        )
        
        print(f"OpenAI 응답: {response.choices[0].message.content}")
        
    except Exception as e:
        print(f"OpenAI 오류: {str(e)}")
        print(f"트레이스백:\n{traceback.format_exc()}")

def debug_llm_bot():
    """LLM Bot의 각 단계별로 디버깅"""
    try:
        print("=== LLM Bot 초기화 ===")
        bot = BurgeriaLLMBot()
        print("초기화 완료")
        
        print("\n=== 메시지 구성 ===")
        user_message = "안녕하세요"
        session_id = "test_session"
        messages = [
            {"role": "system", "content": bot.system_prompt},
            {"role": "user", "content": user_message}
        ]
        print("메시지 구성 완료")
        
        print("\n=== OpenAI API 호출 ===")
        response = bot.client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            tools=bot._get_function_definitions(),
            tool_choice="auto"
        )
        print("API 호출 완료")
        
        response_message = response.choices[0].message
        print(f"응답 메시지: {response_message.content}")
        print(f"Tool calls: {response_message.tool_calls}")
        
    except Exception as e:
        print(f"오류: {str(e)}")
        print(f"트레이스백:\n{traceback.format_exc()}")

if __name__ == "__main__":
    print("1. OpenAI 직접 테스트")
    debug_openai_response()
    
    print("\n" + "="*50)
    print("2. LLM Bot 단계별 테스트") 
    debug_llm_bot()