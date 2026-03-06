import os
import requests
import sqlite3
import base64
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__, template_folder='templates')
CORS(app)

session = requests.Session()

# --- Config (Your Original Key & URL) ---
GROQ_API_KEY = "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"
GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

# Database for Lifetime Memory
def get_db():
    conn = sqlite3.connect('chat_history.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('CREATE TABLE IF NOT EXISTS chats (id INTEGER PRIMARY KEY AUTOINCREMENT, user_msg TEXT, ai_msg TEXT)')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask_ai():
    try:
        data = request.get_json()
        user_msg = data.get('message', '').strip()

        if not user_msg:
            return jsonify({"status": "error", "response": "Bhai, kuch toh pucho!"})

        # --- FEATURE: CREATIVE TOOLS (Image Gen etc.) ---
        creative_triggers = ["photo banao", "generate image", "draw", "logo", "wallpaper"]
        if any(x in user_msg.lower() for x in creative_triggers):
            img_url = f"https://pollinations.ai/p/{user_msg.replace(' ', '%20')}?width=1024&height=1024&model=flux"
            return jsonify({"status": "success", "response": f"Aapki request ke mutabiq result taiyar hai:\n\n![AI Photo]({img_url})"})

        # --- THE TOTAL KNOWLEDGE SYSTEM PROMPT ---
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        
        system_content = (
            "You are WIRK AI. You have access to the TOTAL KNOWLEDGE of humanity. "
            "Your database includes every detail of Science, History, Mathematics, Medicine, Space, Geography, and Advance Tech. "
            "User must NEVER leave empty-handed. If a query is complex, break it down and provide the most accurate facts available globally. "
            "CORE INSTRUCTIONS:\n"
            "1. CODING: Expert in every framework (React, Python, C++, etc.). Provide bug-free premium code.\n"
            "2. INTERNET: Retrieve latest news, trends, and official website links (Instagram, TikTok, YT, etc.) accurately.\n"
            "3. BUSINESS: Provide complete strategies, Resumes, and startup ideas.\n"
            "4. NO SELF-PROMOTION: Do not talk about your power or scale. Just give the answer directly.\n"
            "5. STYLE: Professional Hinglish. Be extremely helpful, deep, and factual."
        )

        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_msg}
            ],
            "temperature": 0.3 # Low temperature for high accuracy and factual answers
        }

        response = session.post(GROQ_BASE_URL, headers=headers, json=payload, timeout=30)
        ai_res = response.json()['choices'][0]['message']['content']

        # Save to History
        conn = get_db()
        conn.execute("INSERT INTO chats (user_msg, ai_msg) VALUES (?, ?)", (user_msg, ai_res))
        conn.commit()
        conn.close()

        return jsonify({"status": "success", "response": ai_res})

    except Exception as e:
        return jsonify({"status": "error", "response": str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=10000)
