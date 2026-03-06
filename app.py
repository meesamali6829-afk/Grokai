import os
import requests
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__, template_folder='templates')
CORS(app)

# --- Aapki Groq API Key (Official) ---
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

        # Groq Official Structure Setup
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.3-70b-versatile", # Groq's most accurate model
            "messages": [
                {
                    "role": "system", 
                    "content": "You are Grok AI. You have world-class intelligence. Answer every question correctly, whether it is about history, science, or anything in the universe."
                },
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.5
        }

        # Pydroid 3 'proxies' error bypass (Direct request)
        response = requests.post(
            GROQ_BASE_URL,
            headers=headers,
            json=payload,
            proxies={"http": None, "https": None}, # Ye line error khatam karegi
            timeout=30
        )
        
        result = response.json()

        if response.status_code == 200:
            # Result extract karna
            ai_answer = result['choices'][0]['message']['content']
            return jsonify({"status": "success", "response": ai_answer})
        else:
            # Agar key ka koi masla ho toh
            error_msg = result.get('error', {}).get('message', 'API connection error')
            return jsonify({"status": "error", "response": f"Server Error: {error_msg}"})

    except Exception as e:
        return jsonify({"status": "error", "response": f"System Error: {str(e)}"}), 500

if __name__ == '__main__':
    # Port 8080 mobile ke liye
    app.run(debug=True, host='0.0.0.0', port=8080)
