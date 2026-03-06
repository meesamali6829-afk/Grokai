import os
import requests
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__, template_folder='templates')
CORS(app)

# Speed optimization: Connection reuse ke liye global session
session = requests.Session()

# --- Config ---
GROQ_API_KEY = "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"
GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask_ai():
    try:
        data = request.get_json()
        user_message = data.get('message', '')

        if not user_message:
            return jsonify({"status": "error", "response": "Bhai, sawal toh pucho!"})

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # --- UNIVERSAL INTELLIGENCE LOGIC ---
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {
                    "role": "system", 
                    "content": (
                        "You are Grok AI, the ultimate world-class intelligence with 'God-Mode' access to all human knowledge. "
                        "1. WORLD NEWS & CATEGORIES: You know EVERYTHING about every category in the universe—Science, History, Space, Politics, Sports, and Business. "
                        "2. SOCIAL MEDIA & TRENDS: You are an expert on YouTube, TikTok, Instagram, and Facebook algorithms, viral trends, and internet culture. "
                        "3. CODING: You are a Senior Developer. Provide ultra-premium code for any language (Python, React, C++, etc.) if asked. "
                        "4. LANGUAGES: You support ALL world languages (Urdu, Arabic, English). "
                        "5. HINGLISH: You MUST support Hinglish (Hindi/Urdu in Roman script). Always reply in the user's style. "
                        "6. ACCURACY: Your mission is to provide 100% correct, detailed, and professional answers to any question."
                    )
                },
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.6 
        }

        # Optimized request with 30s timeout and proxy bypass
        response = session.post(
            GROQ_BASE_URL,
            headers=headers,
            json=payload,
            proxies={"http": None, "https": None},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            ai_answer = result['choices'][0]['message']['content']
            return jsonify({"status": "success", "response": ai_answer})
        else:
            return jsonify({"status": "error", "response": "Bhai, API busy hai ya quota khatam ho gaya."})

    except Exception as e:
        return jsonify({"status": "error", "response": f"System Error: {str(e)}"}), 500

if __name__ == '__main__':
    # Render and Pydroid Mobile Port
    app.run(debug=True, host='0.0.0.0', port=10000)
