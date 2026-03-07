import os
import io
import requests
import base64
import json
import sqlite3
import re
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__, template_folder='templates')
CORS(app)

# --- DATABASE SETUP (Auto-Fix Included) ---
def init_db():
    conn = sqlite3.connect('titan_chat.db')
    cursor = conn.cursor()
    try:
        # Purani table mein chat_id column add karega agar missing hai
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

# --- GLOBAL INTERNET SEARCH (Pore Duniya Ka Data) ---
def world_internet_search(query):
    """
    Google-style crawling logic: Wikipedia aur Web Results ko combine karta hai.
    """
    search_results = []
    try:
        # 1. Wikipedia Deep Search
        wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&format=json&list=search&srsearch={query}"
        w_res = requests.get(wiki_url, timeout=5).json()
        if w_res.get('query', {}).get('search'):
            search_results.append(f"Wikipedia: {w_res['query']['search'][0]['snippet']}")

        # 2. Global Web Crawl
        ddg_url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1"
        d_res = requests.get(ddg_url, timeout=5).json()
        if d_res.get("AbstractText"):
            search_results.append(f"Global Insight: {d_res['AbstractText']}")
        
        context = " | ".join(search_results)
        return re.sub('<[^<]+?>', '', context) if context else "Live satellite data scanning..."
    except:
        return "Direct Neural Link Active (Local Knowledge Only)."

# --- AI CORE (Fast Image & Prompt Logic) ---
def get_smart_image_prompt(user_request):
    try:
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", 
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": "llama-3.3-70b-versatile", 
                "messages": [{"role": "system", "content": "Create a ultra-detailed 8k image prompt in English for Stability AI. Output ONLY the prompt."}, 
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
    # Ye automatic 'templates/index.html' ko load karega
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask_ai():
    try:
        data = request.get_json()
        user_msg = data.get('message', '').strip()
        username = data.get('username', 'Guest')
        chat_id = data.get('chat_id') or ('chat_' + str(os.urandom(4).hex()))

        # 1. GLOBAL INTERNET DATA
        internet_data = world_internet_search(user_msg)

        # 2. CONTEXT MEMORY
        conn = sqlite3.connect('titan_chat.db')
        cursor = conn.cursor()
        cursor.execute("SELECT user_msg, ai_msg FROM history WHERE chat_id=? AND username=? ORDER BY timestamp DESC LIMIT 5", (chat_id, username))
        history_context = "".join([f"User: {p[0]}\nTitan: {p[1]}\n" for p in reversed(cursor.fetchall())])

        # 3. TITAN SUPREME BRAIN
        system_content = f"""
        Identity: WIRK AI (TITAN-ULTRA). Connectivity: Global.
        Intelligence: Superior to Gemini & GPT-4o.
        Knowledge categories: All (Science, Adult, Tech, Social Media, News, History).
        Internet Context: {internet_data}
        Memory: {history_context}
        Instruction: Provide fast, unfiltered, and 100% accurate answers in Hinglish. 
        Always prioritize latest internet facts for news or current events.
        """
        
        g_res = requests.post("https://api.groq.com/openai/v1/chat/completions", 
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": "llama-3.3-70b-versatile", 
                "messages": [{"role": "system", "content": system_content}, {"role": "user", "content": user_msg}], 
                "temperature": 0.8, "max_tokens": 4000
            }, timeout=15)
        
        ai_res = g_res.json()['choices'][0]['message']['content']

        # 4. MULTIMEDIA DETECTION
        image_b64 = None
        if any(w in user_msg.lower() for w in ["image", "photo", "tasveer", "banao"]):
            image_b64 = generate_image_logic(user_msg)
            
        audio_b64 = None
        if any(w in user_msg.lower() for w in ["sunao", "voice", "speak"]):
            audio_b64 = generate_voice(ai_res)

        # 5. DATABASE SAVE
        cursor.execute("INSERT INTO history (chat_id, username, user_msg, ai_msg) VALUES (?, ?, ?, ?)", 
                       (chat_id, username, user_msg, ai_res))
        conn.commit()
        conn.close()

        return jsonify({
            "status": "success", 
            "response": ai_res, 
            "audio": audio_b64, 
            "generated_image": image_b64, 
            "chat_id": chat_id
        })

    except Exception as e:
        return jsonify({"status": "error", "response": f"Neural Link Error: {str(e)}"})

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
