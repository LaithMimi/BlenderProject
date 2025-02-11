from flask import Flask, request, jsonify, render_template, g
import sqlite3
from transformers import AutoTokenizer, AutoModelForQuestionAnswering
from bidi.algorithm import get_display
import arabic_reshaper
import os
import torch
from flask_cors import CORS
import requests  # Import requests for Gemini API calls

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Load AraBERT model
model_name = "aubmindlab/bert-base-arabert"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForQuestionAnswering.from_pretrained(model_name)

# Load Gemini API key from environment variable
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    print("Warning: Gemini API key not found. The Gemini API will not be called.")

DATABASE = "materials.db"

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# Fetch material by level and week
def get_content_by_level_week(level, week):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT content FROM materials WHERE level = ? AND week = ?", (level, week))
    result = cursor.fetchone()
    return result[0] if result else "No content found for the selected week."

# Generate response with AraBERT
def ask_arabert(question, context):
    inputs = tokenizer.encode_plus(question, context, return_tensors="pt", truncation=True, padding=True)
    
    # Debug: Print the input tokens
    print("Input IDs:", inputs.input_ids)
    print("Attention Mask:", inputs.attention_mask)
    
    outputs = model(**inputs)
    
    start_idx = torch.argmax(outputs.start_logits)
    end_idx = torch.argmax(outputs.end_logits)
    
    # Ensure the end index is greater than or equal to the start index
    if end_idx < start_idx:
        end_idx = start_idx
    
    # Decode the tokens and clean up the response
    answer_tokens = inputs.input_ids[0][start_idx:end_idx + 1]
    answer = tokenizer.decode(answer_tokens, skip_special_tokens=True)
    
    # Debug: Print the decoded answer
    print("Decoded Answer:", answer)
    
    return answer

# Fallback to Gemini API
def ask_gemini(question, context, preferred_language):
    if not gemini_api_key:
        return "Gemini API key is not set. Please provide a valid API key to use this feature."
    
    url = "https://gemini-api-url.com/v1/ask"  # Update with the actual Gemini API URL
    headers = {
        "Authorization": f"Bearer {gemini_api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "context": context,
        "question": question,
        "language": preferred_language
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Raise an exception for HTTP errors
        result = response.json()
        return result.get("answer", "No answer found.")
    except requests.exceptions.RequestException as e:
        print(f"Error using Gemini API: {e}")
        return "Error fetching response from Gemini API."

# Transliteration: Arabic → Hebrew
def transliterate_to_hebrew(text):
    transliteration_rules = {
        "ا": "א", "ب": "ב", "ت": "ת", "ث": "ת'", "ج": "ג", "ح": "ח", "خ": "כ'",
        "د": "ד", "ذ": "ד'", "ر": "ר", "ز": "ז", "س": "ס", "ش": "ש", "ص": "צ",
        "ض": "צ'", "ط": "ט", "ظ": "ט'", "ع": "ע", "غ": "ע'", "ف": "פ", "ق": "ק",
        "ك": "כ", "ل": "ל", "م": "מ", "ن": "נ", "ه": "ה", "و": "ו", "ي": "י",
        "ء": "'", "ئ": "'", "ى": "י", "ة": "ה"
    }
    hebrew_text = ''.join([transliteration_rules.get(char, char) for char in text])
    return hebrew_text

# Transliteration: Arabic → English
def transliterate_to_english(text):
    transliteration_rules = {
        "ا": "a", "ب": "b", "ت": "t", "ث": "th", "ج": "j", "ح": "h", "خ": "kh",
        "د": "d", "ذ": "dh", "ر": "r", "ز": "z", "س": "s", "ش": "sh", "ص": "s",
        "ض": "d", "ط": "t", "ظ": "th", "ع": "a'", "غ": "gh", "ف": "f", "ق": "q",
        "ك": "k", "ل": "l", "م": "m", "ن": "n", "ه": "h", "و": "w", "ي": "y",
        "ء": "'", "ئ": "i", "ى": "a", "ة": "h"
    }
    english_text = ''.join([transliteration_rules.get(char, char) for char in text])
    return english_text

# Route for saving user information
@app.route("/save_user", methods=["POST"])
def save_user():
    user_data = request.json
    return jsonify({"message": "User data received!", "data": user_data})

# API Endpoint
@app.route("/ask", methods=["POST"])
def ask():
    data = request.json
    level, week, question, gender, preferred_language = (
        data["level"], data["week"], data["question"], data["gender"], data["language"]
    )

    context = get_content_by_level_week(level, week)
    if context == "No content found for the selected week.":
        return jsonify({"answer": context})

    try:
        answer = ask_arabert(question, context)
    except Exception as e:
        print(f"Error using AraBERT: {e}")
        answer = ask_gemini(question, context, preferred_language)

    if preferred_language == "arabic":
        response = answer
    elif preferred_language == "transliteration-hebrew":
        response = transliterate_to_hebrew(answer)
    elif preferred_language == "transliteration-english":
        response = transliterate_to_english(answer)
    else:
        response = "Invalid language option."

    return jsonify({"answer": response})

# Serve Frontend
@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)