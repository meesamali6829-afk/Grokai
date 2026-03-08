import os
import io
import requests
import base64
import json
import sqlite3
import re
from datetime import datetime
import time
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__, template_folder='templates') 
CORS(app)

# --- DATABASE SETUP (Persistent Neural Archive) ---
def init_db():
    conn = sqlite3.connect('titan_chat.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS history 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                     chat_id TEXT, username TEXT, user_msg TEXT, ai_msg TEXT, 
                     timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                     image_url TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- API KEYS ---
OPENROUTER_API_KEY = "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"
STABILITY_KEY = "sk-13pC5Gw0GRaPyKhPaoquHsww7aXJLN3NP5r2yGmwDQFJOpE3"

# --- SUPREME KNOWLEDGE SCANNER ---
def deep_knowledge_search(query):
    context_data = []
    try:
        wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&format=json&list=search&srsearch={query}&utf8=1"
        wiki_res = requests.get(wiki_url, timeout=5).json()
        if wiki_res.get('query', {}).get('search'):
            snippet = re.sub('<[^<]+?>', '', wiki_res['query']['search'][0]['snippet'])
            context_data.append(f"Wikipedia Source: {snippet}")
        return " | ".join(context_data) if context_data else "Titan Grid Synchronized"
    except:
        return "Global Grid Connection Stable."

# --- TITAN IMAGE RENDERER ---
def generate_image(prompt):
    try:
        enhanced_prompt = f"{prompt}, professional masterpiece, 8k resolution, cinematic lighting, ultra-detailed"
        url = "https://api.stability.ai/v1/generation/stable-diffusion-v1-6/text-to-image"
        headers = {"Accept": "application/json", "Authorization": f"Bearer {STABILITY_KEY}"}
        body = {"text_prompts": [{"text": enhanced_prompt}], "cfg_scale": 10, "height": 512, "width": 512, "steps": 40}
        res = requests.post(url, headers=headers, json=body)
        if res.status_code == 200:
            return f"data:image/png;base64,{res.json()['artifacts'][0]['base64']}"
    except:
        return None

# --- CORE NEURAL ENGINE ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask_ai():
    try:
        data = request.get_json()
        user_msg = data.get('message', '').strip()
        username = data.get('username', 'Guest')
        chat_id = data.get('chat_id') or ('chat_' + datetime.now().strftime("%Y%m%d_%H%M%S"))
        
        # 1. Image Trigger
        image_url = None
        if any(x in user_msg.lower() for x in ['image', 'photo', 'draw', 'banao', 'art', 'picture']):
            image_url = generate_image(user_msg)

        # 2. Live Intel Sync
        live_intel = deep_knowledge_search(user_msg)

        # 3. UNLIMITED MEMORY RECALL (No LIMIT used here)
        conn = sqlite3.connect('titan_chat.db')
        cursor = conn.cursor()
        # Unlimited history for this specific chat_id
        cursor.execute("SELECT user_msg, ai_msg FROM history WHERE chat_id=? ORDER BY timestamp ASC", (chat_id,))
        rows = cursor.fetchall()
        
        full_context = ""
        for r in rows:
            full_context += f"User: {r[0]}\nAI: {r[1]}\n"

        # 4. GOD-MODE SYSTEM PROMPT
        system_prompt = f"""
        [STATUS: GOD-MODE ACTIVATED]
        [MEMORY: UNLIMITED RECALL]
        Identity: WIRK AI TITAN-ULTRA. 
        Live Data: {live_intel}
        
        Protocol:
        1. Aapke paas is chat ki poori history niche 'Chat Archive' mein mojood hai.
        2. Agar user kahe "uper maine kya kaha?" ya "hum kis bare mein baat kar rahe the?", to archive se dekh kar foran jawab do.
        3. Jab tak user topic na badle, context ko mat choro. Continuous conversation maintain rakho.
        4. Language: Hinglish. No apologies, direct answers.

        Chat Archive (Full History):
        {full_context}
        """

        # 5. OpenRouter Call
        payload = {
            "model": "google/gemini-2.0-flash-001", 
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg}
            ],
            "temperature": 0.3 
        }
        headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
        
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=50)
        ai_res = response.json()['choices'][0]['message']['content']

        # 6. Archive Storage
        cursor.execute("INSERT INTO history (chat_id, username, user_msg, ai_msg, image_url) VALUES (?, ?, ?, ?, ?)", 
                       (chat_id, username, user_msg, ai_res, image_url))
        conn.commit()
        conn.close()

        return jsonify({"status": "success", "response": ai_res, "image_url": image_url, "chat_id": chat_id})

    except Exception as e:
        return jsonify({"status": "error", "response": "Neural Link Interrupted. Re-syncing..."})

@app.route('/get_sidebar_history', methods=['POST'])
def get_sidebar_history():
    data = request.get_json()
    username = data.get('username', 'Guest')
    conn = sqlite3.connect('titan_chat.db')
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id, user_msg, MAX(timestamp) FROM history WHERE username=? GROUP BY chat_id ORDER BY timestamp DESC", (username,))
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"chat_id": r[0], "title": r[1][:35] + "..."} for r in rows])

@app.route('/load_chat', methods=['POST'])
def load_chat():
    data = request.get_json()
    chat_id = data.get('chat_id')
    conn = sqlite3.connect('titan_chat.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_msg, ai_msg, image_url FROM history WHERE chat_id=? ORDER BY timestamp ASC", (chat_id,))
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"user": r[0], "ai": r[1], "image": r[2]} for r in rows])

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=10000)
