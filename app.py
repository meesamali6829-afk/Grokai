import os
import requests
import sqlite3
import base64
import json
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import io

# PyPDF2 install check
try:
    import PyPDF2
except ImportError:
    print("PyPDF2 not found. Please run: pip install PyPDF2")

app = Flask(__name__, template_folder='templates')
CORS(app)

# --- API KEYS ---
GROQ_API_KEY = "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"
GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
OPENAI_API_KEY = "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"
ELEVENLABS_API_KEY = "sk_261cdc0cfa5d3119a588a72f045138600e0679ca445dd9b6"

# --- Database Setup (Schema Aware) ---
def get_db():
    conn = sqlite3.connect('chat_history.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    # 1. Pehle table banayein agar nahi hai
    conn.execute('''CREATE TABLE IF NOT EXISTS chats 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  username TEXT,
                  user_msg TEXT, ai_msg TEXT, 
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # 2. Check karein agar 'username' column purani database mein missing hai
    cursor = conn.execute("PRAGMA table_info(chats)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'username' not in columns:
        try:
            conn.execute('ALTER TABLE chats ADD COLUMN username TEXT DEFAULT "Guest"')
            conn.commit()
            print("System: Database updated with 'username' column.")
        except Exception as e:
            print(f"System: Update failed (might be normal): {e}")
            
    conn.commit()
    conn.close()

# Initialize Database
init_db()

# --- KNOWLEDGE ENGINES ---

def wikipedia_search_sim(query):
    return f"[INTERNET SEARCH ACTIVE: Scanned Wikipedia for '{query}']"

def extract_text_from_pdf(base64_pdf):
    try:
        pdf_data = base64.b64decode(base64_pdf.split(',')[1])
        pdf_file = io.BytesIO(pdf_data)
        reader = PyPDF2.PdfReader(pdf_file)
        text = "".join([page.extract_text() for page in reader.pages])
        return text[:15000]
    except Exception as e: 
        return f"PDF Analysis Failed: {str(e)}"

def generate_voice(text):
    try:
        url = "https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4lfsNq6t29AM"
        headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
        payload = {
            "text": text[:1000], 
            "model_id": "eleven_multilingual_v2", 
            "voice_settings": {"stability": 0.4, "similarity_boost": 0.8}
        }
        res = requests.post(url, json=payload, headers=headers)
        return base64.b64encode(res.content).decode('utf-8') if res.status_code == 200 else None
    except: return None

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_history', methods=['GET'])
def get_history():
    username = request.args.get('username', 'Guest')
    conn = get_db()
    # Sirf us user ki history nikalein jo logged in hai
    chats = conn.execute('SELECT id, user_msg FROM chats WHERE username = ? ORDER BY id DESC LIMIT 50', (username,)).fetchall()
    conn.close()
    return jsonify([dict(ix) for ix in chats])

@app.route('/get_chat/<int:chat_id>', methods=['GET'])
def get_chat(chat_id):
    conn = get_db()
    chat = conn.execute('SELECT user_msg, ai_msg FROM chats WHERE id = ?', (chat_id,)).fetchone()
    conn.close()
    if chat:
        return jsonify({
            "status": "success", 
            "history": [
                {"role": "user", "content": chat['user_msg']}, 
                {"role": "ai", "content": chat['ai_msg']}
            ]
        })
    return jsonify({"status": "error"})

@app.route('/ask', methods=['POST'])
def ask_ai():
    try:
        data = request.get_json()
        user_msg = data.get('message', '').strip()
        username = data.get('username', 'Guest') 
        user_image = data.get('image')
        user_pdf = data.get('pdf')

        # Multi-modal Analysis
        img_info = ""
        if user_image:
            v_res = requests.post("https://api.openai.com/v1/chat/completions", 
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={
                    "model": "gpt-4o", 
                    "messages": [{"role": "user", "content": [
                        {"type": "text", "text": "Analyze image detailed."}, 
                        {"type": "image_url", "image_url": {"url": user_image}}
                    ]}]
                })
            img_info = f"\n[IMAGE SCAN: {v_res.json()['choices'][0]['message']['content']}]"

        pdf_info = f"\n[DOCUMENT DATA: {extract_text_from_pdf(user_pdf)}]" if user_pdf else ""
        web_info = wikipedia_search_sim(user_msg)

        system_content = f"""
        Identity: WIRK AI (Titan-Ultra). User: {username}.
        Instructions: Use Hinglish. Master in all categories. Be concise but brilliant.
        Live Context: {web_info} {img_info} {pdf_info}
        """

        # Main AI Response (Groq)
        g_res = requests.post(GROQ_BASE_URL, headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": "llama-3.3-70b-versatile", 
                "messages": [
                    {"role": "system", "content": system_content}, 
                    {"role": "user", "content": user_msg if user_msg else "Describe the attached file."}
                ], 
                "temperature": 0.4
            })
        
        ai_res = g_res.json()['choices'][0]['message']['content']
        audio = generate_voice(ai_res)

        # Database Save
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO chats (username, user_msg, ai_msg) VALUES (?, ?, ?)", 
                       (username, user_msg if user_msg else "[File/Image]", ai_res))
        new_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return jsonify({"status": "success", "response": ai_res, "audio": audio, "chat_id": new_id})
    except Exception as e:
        return jsonify({"status": "error", "response": f"Titan Error: {str(e)}"})

if __name__ == '__main__':
    # Flask app start
    app.run(debug=True, host='0.0.0.0', port=10000)
