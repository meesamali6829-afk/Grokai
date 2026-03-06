import os
import requests
import sqlite3
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from functools import lru_cache

app = Flask(__name__, template_folder='templates')
CORS(app)

# --- Config & Speed Optimization ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "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")
GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

# Global Session: Isse baar-baar connection banane ka time bachega (Speed boost)
session = requests.Session()
session.proxies = {"http": None, "https": None}

def get_db_connection():
    # check_same_thread=False se multi-threading fast ho jati hai
    conn = sqlite3.connect('chat_history.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS chats 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_msg TEXT, ai_msg TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_history', methods=['GET'])
def get_history():
    conn = get_db_connection()
    # Speed Fix: Limit history to last 20 for faster sidebar loading
    rows = conn.execute("SELECT id, user_msg FROM chats ORDER BY id DESC LIMIT 20").fetchall()
    history = [{"id": row['id'], "title": row['user_msg'][:30]} for row in rows]
    conn.close()
    return jsonify(history)

@app.route('/ask', methods=['POST'])
def ask_ai():
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({"status": "error", "response": "Bhai, sawal toh pucho!"})

        # --- Image Generation Logic ---
        if any(word in user_message.lower() for word in ["banao", "image", "photo", "generate"]):
            image_url = f"https://pollinations.ai/p/{user_message.replace(' ', '%20')}?width=1024&height=1024&seed=42"
            return jsonify({"status": "success", "response": f"Bhai, aapki image taiyar hai: ![image]({image_url})", "type": "image"})

        # API Payload
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "You are Grok AI. World-class intelligence. Answer concisely."},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.6,
            "max_tokens": 1024 # Isse response delay kam hota hai
        }

        # Optimized Request using global session
        response = session.post(
            GROQ_BASE_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=15 # Time kam kar diya taaki loading lambi na khinche
        )
        
        if response.status_code == 200:
            ai_answer = response.json()['choices'][0]['message']['content']
            
            # Database Save (Fast Insert)
            conn = get_db_connection()
            conn.execute("INSERT INTO chats (user_msg, ai_msg) VALUES (?, ?)", (user_message, ai_answer))
            conn.commit()
            conn.close()

            return jsonify({"status": "success", "response": ai_answer})
        else:
            return jsonify({"status": "error", "response": "API busy hai, thodi der baad try karein."})

    except Exception as e:
        return jsonify({"status": "error", "response": f"Speed Error: {str(e)}"}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400
    return jsonify({"status": "success", "message": "Uploaded!"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    # Threaded=True se multiple users ko ek sath handle karega
    app.run(debug=False, host='0.0.0.0', port=port, threaded=True)
