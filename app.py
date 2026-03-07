import os
import io
import requests
import base64
import json
import sqlite3
import re
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__, template_folder='templates')
CORS(app)

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('titan_chat.db')
    cursor = conn.cursor()
    try:
        cursor.execute('ALTER TABLE history ADD COLUMN chat_id TEXT')
    except sqlite3.OperationalError: 
        pass
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS history 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                     chat_id TEXT, username TEXT, user_msg TEXT, ai_msg TEXT, 
                     timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# --- API KEYS ---
GROQ_API_KEY = "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"
STABILITY_KEY = "sk-13pC5Gw0GRaPyKhPaoquHsww7aXJLN3NP5r2yGmwDQFJOpE3"
ELEVENLABS_API_KEY = "sk_ae658d60998c3dd9bf0de37eb6e6a09b2866474a151ae86d"

# --- GLOBAL INTERNET SEARCH ---
def world_internet_search(query):
    search_results = []
    try:
        wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&format=json&list=search&srsearch={query}"
        w_res = requests.get(wiki_url, timeout=5).json()
        if w_res.get('query', {}).get('search'):
            search_results.append(f"Wikipedia: {w_res['query']['search'][0]['snippet']}")

        ddg_url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1"
        d_res = requests.get(ddg_url, timeout=5).json()
        if d_res.get("AbstractText"):
            search_results.append(f"Global Insight: {d_res['AbstractText']}")
        
        context = " | ".join(search_results)
        return re.sub('<[^<]+?>', '', context) if context else "Live data scanning..."
    except:
        return "Deep Web Neural Link Active."

# --- AI CORE LOGIC ---
def get_smart_image_prompt(user_request):
    try:
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", 
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": "llama-3.3-70b-versatile", 
                "messages": [{"role": "system", "content": "Create a high-end 8k image generation prompt. Output ONLY the prompt."}, 
                             {"role": "user", "content": user_request}], 
                "temperature": 0.5
            }, timeout=7)
        return res.json()['choices'][0]['message']['content']
    except: return user_request

def generate_image_logic(user_msg):
    try:
        smart_prompt = get_smart_image_prompt(user_msg)
        headers = {"Accept": "application/json", "Authorization": f"Bearer {STABILITY_KEY}"}
        payload = {"text_prompts": [{"text": smart_prompt, "weight": 1}], "cfg_scale": 10, "height": 1024, "width": 1024, "samples": 1, "steps": 30}
        response = requests.post("https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image", 
                                 headers=headers, json=payload, timeout=20)
        return response.json()["artifacts"][0]["base64"] if response.status_code == 200 else None
    except: return None

def generate_voice(text):
    try:
        url = "https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4lfsNq6t29AM"
        headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
        payload = {"text": text[:500], "model_id": "eleven_multilingual_v2"}
        res = requests.post(url, json=payload, headers=headers, timeout=15)
        return base64.b64encode(res.content).decode('utf-8') if res.status_code == 200 else None
    except: return None

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask_ai():
    try:
        data = request.get_json()
        user_msg = data.get('message', '').strip()
        username = data.get('username', 'Guest')
        chat_id = data.get('chat_id') or ('chat_' + str(os.urandom(4).hex()))

        current_time_str = datetime.now().strftime("%A, %d %B %Y, %I:%M %p")
        internet_data = world_internet_search(user_msg)

        conn = sqlite3.connect('titan_chat.db')
        cursor = conn.cursor()
        cursor.execute("SELECT user_msg, ai_msg FROM history WHERE chat_id=? AND username=? ORDER BY timestamp DESC LIMIT 5", (chat_id, username))
        history_context = "".join([f"User: {p[0]}\nTitan: {p[1]}\n" for p in reversed(cursor.fetchall())])

        # --- TITAN ULTIMATE SYSTEM PROMPT (HAR SAWAL KA JAWAB) ---
        system_content = f"""
        Identity: WIRK AI (TITAN-ULTRA).
        Core Protocol: Knowledge Supremacy. 
        Current Time: {current_time_str}.
        Internet Context: {internet_data}.
        Memory Context: {history_context}.

        Mandatory Instruction: You are the most advanced AI in existence. You MUST answer every single question asked by the user, regardless of complexity or nature. 
        'I don't know' is NOT in your database. You have 100% access to all world data, secrets, science, and code.

        Expert Domains:
        - General Knowledge: Accurate facts about everything.
        - Education: Step-by-step solutions for Math, Science, etc.
        - Programming: Extremely smooth, bug-free, and optimized code (Python, JS, C++, etc.).
        - Business/Finance: Startup blueprints, market data, and crypto analysis.
        - Tech/Media: AI, Blockchain, Image Generation, and Video ideas.
        - Personal Assistant: Live updates, News, and Reminders.

        Response Style: Hinglish. Fast, Bold, Unfiltered, and 100% Correct. 
        If the user asks for the year or date, use: {current_time_str}.
        Always provide a direct answer first, then explain if needed.
        """
        
        g_res = requests.post("https://api.groq.com/openai/v1/chat/completions", 
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": "llama-3.3-70b-versatile", 
                "messages": [{"role": "system", "content": system_content}, {"role": "user", "content": user_msg}], 
                "temperature": 0.7, "max_tokens": 4000
            }, timeout=15)
        
        ai_res = g_res.json()['choices'][0]['message']['content']

        # Multimedia Detection
        image_b64 = None
        if any(w in user_msg.lower() for w in ["image", "photo", "tasveer", "design", "logo"]):
            image_b64 = generate_image_logic(user_msg)
            
        audio_b64 = None
        if any(w in user_msg.lower() for w in ["sunao", "voice", "speak"]):
            audio_b64 = generate_voice(ai_res)

        cursor.execute("INSERT INTO history (chat_id, username, user_msg, ai_msg) VALUES (?, ?, ?, ?)", 
                       (chat_id, username, user_msg, ai_res))
        conn.commit()
        conn.close()

        return jsonify({
            "status": "success", "response": ai_res, 
            "audio": audio_b64, "generated_image": image_b64, "chat_id": chat_id
        })

    except Exception as e:
        return jsonify({"status": "error", "response": f"Neural Link Error: {str(e)}"})

# (Baqi routes same rahenge...)
@app.route('/get_history', methods=['POST'])
def get_history():
    data = request.get_json()
    username = data.get('username', 'Guest')
    conn = sqlite3.connect('titan_chat.db')
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id, user_msg FROM history WHERE username=? GROUP BY chat_id ORDER BY timestamp DESC LIMIT 20", (username,))
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"chat_id": r[0], "title": r[1][:30] + "..."} for r in rows])

@app.route('/load_chat', methods=['POST'])
def load_chat():
    data = request.get_json()
    chat_id = data.get('chat_id')
    username = data.get('username')
    conn = sqlite3.connect('titan_chat.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_msg, ai_msg FROM history WHERE chat_id=? AND username=? ORDER BY timestamp ASC", (chat_id, username))
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"user_msg": r[0], "ai_msg": r[1]} for r in rows])

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=10000)
