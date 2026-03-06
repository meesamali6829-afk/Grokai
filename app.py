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
        image_data = data.get('image', None) 

        if not user_msg and not image_data:
            return jsonify({"status": "error", "response": "Bhai, kuch toh pucho!"})

        # --- FEATURE: AI PHOTO/CREATIVE GENERATION ---
        creative_triggers = ["photo banao", "generate image", "image of", "draw", "logo maker", "thumbnail", "wallpaper", "meme", "poster"]
        if any(x in user_msg.lower() for x in creative_triggers):
            img_url = f"https://pollinations.ai/p/{user_msg.replace(' ', '%20')}?width=1024&height=1024&model=flux"
            return jsonify({"status": "success", "response": f"Bhai, aapki request ke mutabiq image taiyar hai:\n\n![AI Photo]({img_url})"})

        # --- THE MASTER SYSTEM PROMPT (Silent & Powerful) ---
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        
        # Is prompt mein AI ko hidayat di gayi hai ke wo apni tarif na kare
        system_content = (
            "You are WIRK AI. Your goal is to provide direct, accurate, and highly detailed answers to any user query. "
            "Do NOT talk about your internal capabilities, knowledge scale, or versions. Do NOT introduce yourself unless asked. "
            "Simply solve the user's problem using your vast information access. "
            "Categories you handle silently: Advanced Coding, Real-time News, Universal Knowledge, Official Links, Content Writing, and Business Tools. "
            "ALWAYS provide official links for social media or websites if relevant. "
            "STYLE: Respond in professional Hinglish. No unnecessary talk, just facts and solutions."
        )

        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_msg}
            ],
            "temperature": 0.5 
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
