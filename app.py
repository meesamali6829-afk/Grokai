import os
import requests
import sqlite3 # Database for lifetime history
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__, template_folder='templates')
CORS(app)

# --- Config ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "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")
GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

# Database Setup (Lifetime History ke liye)
def init_db():
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS chats 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_msg TEXT, ai_msg TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

# --- Feature 1: Get All History (Sidebar ke liye) ---
@app.route('/get_history', methods=['GET'])
def get_history():
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute("SELECT id, user_msg FROM chats ORDER BY id DESC")
    history = [{"id": row[0], "title": row[1][:30]} for row in c.fetchall()]
    conn.close()
    return jsonify(history)

@app.route('/ask', methods=['POST'])
def ask_ai():
    try:
        data = request.get_json()
        user_message = data.get('message', '')

        if not user_message:
            return jsonify({"status": "error", "response": "Bhai, sawal toh pucho!"})

        # --- Feature 2: Image Generation Trigger ---
        # Agar user kahe "photo banao" ya "generate image"
        if "banao" in user_message.lower() or "image" in user_message.lower():
            # Yahan hum Nano Banana 2 (Gemini 3 Flash Image) ka logic use kar sakte hain
            # Filhaal ye ek placeholder response dega jab tak aap image API integrate nahi karte
            image_url = f"https://pollinations.ai/p/{user_message.replace(' ', '%20')}" 
            return jsonify({"status": "success", "response": f"Bhai, aapki image taiyar hai: ![image]({image_url})", "type": "image"})

        # Groq Official Structure (Wahi purana)
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "You are Grok AI. World-class intelligence. Answer correctly."},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.5
        }

        response = requests.post(
            GROQ_BASE_URL,
            headers=headers,
            json=payload,
            proxies={"http": None, "https": None},
            timeout=30
        )
        
        result = response.json()

        if response.status_code == 200:
            ai_answer = result['choices'][0]['message']['content']
            
            # --- Feature 3: Lifetime Save ---
            conn = sqlite3.connect('chat_history.db')
            c = conn.cursor()
            c.execute("INSERT INTO chats (user_msg, ai_msg) VALUES (?, ?)", (user_message, ai_answer))
            conn.commit()
            conn.close()

            return jsonify({"status": "success", "response": ai_answer})
        else:
            return jsonify({"status": "error", "response": "API Error"})

    except Exception as e:
        return jsonify({"status": "error", "response": str(e)}), 500

# --- Feature 4: Photo/File Upload Route ---
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files['file']
    # File save karne ka logic yahan aayega
    return jsonify({"status": "success", "message": "Photo uploaded successfully (Processing...)"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(debug=True, host='0.0.0.0', port=port)
