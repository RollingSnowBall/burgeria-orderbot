import os
from dotenv import load_dotenv
from llm_integration import BurgeriaLLMBot

load_dotenv()

def test_ordering_flow():
    """Test the complete ordering flow"""
    bot = BurgeriaLLMBot()
    session_id = "test_session_llm"
    conversation_history = []
    
    print("=== Burgeria LLM Bot 테스트 ===")
    print("주문 관련 질문만 처리하고, 그 외 질문은 거절하는지 테스트합니다.\n")
    
    test_cases = [
        # 주문 관련 질문들
        "안녕하세요! 양념감자 주문하고 싶어요",
        "2번으로 주세요. 치즈토핑도 추가해주세요",
        "장바구니 확인해주세요",
        "한우불고기버거 세트도 추가해주세요. 음료는 아이스티로 바꿔주세요",
        "총 얼마인가요?",
        "주문 완료해주세요",
        
        # 주문과 무관한 질문들 (거절되어야 함)
        "오늘 날씨 어때요?",
        "롯데리아 매장 위치 알려주세요",
        "햄버거 만드는 방법 알려주세요",
        "다른 브랜드 햄버거 추천해주세요"
    ]
    
    for i, test_message in enumerate(test_cases, 1):
        print(f"\n--- 테스트 {i} ---")
        print(f"사용자: {test_message}")
        
        response = bot.chat(
            user_message=test_message,
            session_id=session_id,
            conversation_history=conversation_history
        )
        
        print(f"봇: {response}")
        
        # 대화 이력 업데이트
        conversation_history.append({"role": "user", "content": test_message})
        conversation_history.append({"role": "assistant", "content": response})
        
        # 이력 길이 제한
        if len(conversation_history) > 20:
            conversation_history = conversation_history[-20:]
        
        print("-" * 50)

def interactive_test():
    """Interactive test mode"""
    bot = BurgeriaLLMBot()
    session_id = "interactive_session"
    conversation_history = []
    
    print("=== Burgeria Interactive Test ===")
    print("직접 대화해보세요! (종료하려면 'quit' 입력)")
    print("=" * 50)
    
    while True:
        user_input = input("\n사용자: ").strip()
        
        if user_input.lower() in ['quit', 'exit', '종료']:
            print("테스트를 종료합니다.")
            break
        
        if not user_input:
            continue
        
        response = bot.chat(
            user_message=user_input,
            session_id=session_id,
            conversation_history=conversation_history
        )
        
        print(f"봇: {response}")
        
        # 대화 이력 업데이트
        conversation_history.append({"role": "user", "content": user_input})
        conversation_history.append({"role": "assistant", "content": response})
        
        # 이력 길이 제한
        if len(conversation_history) > 20:
            conversation_history = conversation_history[-20:]

if __name__ == "__main__":
    if not os.getenv('OPENAI_API_KEY'):
        print("ERROR: OPENAI_API_KEY가 설정되지 않았습니다.")
        print("1. .env 파일을 생성하고 API 키를 설정하세요.")
        print("2. 또는 환경변수로 설정하세요: set OPENAI_API_KEY=your_key_here")
        exit(1)
    
    print("테스트 모드를 선택하세요:")
    print("1. 자동 테스트 (미리 정의된 시나리오)")
    print("2. 대화형 테스트 (직접 입력)")
    
    choice = input("선택 (1 또는 2): ").strip()
    
    if choice == "1":
        test_ordering_flow()
    elif choice == "2":
        interactive_test()
    else:
        print("잘못된 선택입니다.")