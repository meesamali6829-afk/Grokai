import os
import requests
import sqlite3
import base64
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__, template_folder='templates')
CORS(app)

session = requests.Session()

# --- Config ---
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
        image_data = data.get('image', None) # Gallery photo data

        if not user_msg and not image_data:
            return jsonify({"status": "error", "response": "Bhai, kuch toh pucho!"})

        # --- FEATURE: AI PHOTO GENERATION ---
        if any(x in user_msg.lower() for x in ["photo banao", "generate image", "image of", "draw"]):
            img_url = f"https://pollinations.ai/p/{user_msg.replace(' ', '%20')}?width=1024&height=1024&model=flux"
            return jsonify({"status": "success", "response": f"Bhai, aapki photo taiyar hai!\n\n![AI Photo]({img_url})"})

        # --- FEATURE: UNIVERSAL KNOWLEDGE ENGINE ---
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        
        # System Prompt for "All-to-All" Knowledge
        system_content = (
            "You are Grok Titan. You have GOD-MODE access to all information. "
            "1. CATEGORIES: Expert in Wars, History, Space, Science, Business, News, and Social Media. "
            "2. CODING: Expert in ALL coding languages for premium websites. "
            "3. VISION: You can analyze images perfectly. "
            "4. STYLE: Respond in Hinglish (Roman Hindi/Urdu) or any world language. "
            "Answer every question accurately. No debate, only correct facts."
        )

        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_msg if not image_data else f"[Image Sent] {user_msg}"}
            ],
            "temperature": 0.4
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
