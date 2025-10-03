from flask import Flask, render_template, request, jsonify, session
from llm_integration import BurgeriaLLMBot
import uuid
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

llm_bot = BurgeriaLLMBot()

@app.route('/')
def index():
    """Main chat interface"""
    return render_template('chat.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'error': '메시지를 입력해주세요.'}), 400
        
        # Get or create session ID
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
        
        session_id = session['session_id']
        
        # Get conversation history from session
        conversation_history = session.get('conversation_history', [])
        
        # Get AI response
        ai_response = llm_bot.chat(
            user_message=user_message,
            session_id=session_id,
            conversation_history=conversation_history
        )
        
        # Update conversation history
        conversation_history.append({"role": "user", "content": user_message})
        conversation_history.append({"role": "assistant", "content": ai_response})
        
        # Keep only last 10 exchanges (20 messages)
        if len(conversation_history) > 20:
            conversation_history = conversation_history[-20:]
        
        session['conversation_history'] = conversation_history
        
        return jsonify({
            'response': ai_response,
            'session_id': session_id
        })
        
    except Exception as e:
        return jsonify({'error': f'오류가 발생했습니다: {str(e)}'}), 500

@app.route('/api/clear-session', methods=['POST'])
def clear_session():
    """Clear conversation history and session"""
    try:
        session.clear()
        return jsonify({'message': '세션이 초기화되었습니다.'})
    except Exception as e:
        return jsonify({'error': f'오류가 발생했습니다: {str(e)}'}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'Burgeria Order Bot is running!'})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    print("=== Burgeria Order Bot Server ===")
    print(f"Starting server on http://localhost:{port}")
    print("Press Ctrl+C to stop")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )