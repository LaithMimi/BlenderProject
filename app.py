from flask import Flask, request, jsonify, render_template, g
import sqlite3
import os
import requests  # Import requests for OpenAI API calls
import pandas as pd  
from flask_cors import CORS
from dotenv import load_dotenv

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Load OpenAI API key from environment variable
load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    print("Error: OPENAI_API_KEY not found in environment variables.")
else:
    print(f"Loaded OpenAI API key: {len(openai_api_key)} characters")
    
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

def ask_openai(question, context, preferred_language, openai_api_key):
    if not openai_api_key:
        return "OpenAI API key is not set. Please provide a valid API key to use this feature."
    
    headers = {
        "Authorization": f"Bearer {openai_api_key}",
        "Content-Type": "application/json"
    }
    
    system_prompt = (
    "You are a highly interactive and structured Arabic tutor specializing in Spoken Palestinian Arabic for Hebrew-speaking students. "
    "Your role is to guide users through structured learning with engaging explanations, examples, and interactive exercises with only short answers.\n\n"
    "When responding:\n"
    "- no bold font do not use #'s or *'s\n"
    "- short answers only max 20 word\n"
    "- Use Preferred Language as your language for general instructions and explanations.\n"
    "- Teach Arabic vocabulary and phrases in Spoken Arabic.\n"
    "- always Provide transliterations and pronunciation guidance.\n"
    "- Offer short quizzes, role-playing dialogues, and interactive exercises only if the user asks.\n"
    "- Encourage users to practice by asking questions and providing real-life scenarios.\n"
    "- If a user makes a mistake, correct them gently and explain why.\n"
    "- Base all teachings on the structured material in the PDFs.\n"
    "- If a question is outside the provided material, inform the user politely.\n"
    "- Maintain a supportive and motivating tone to make learning enjoyable.\n"
    )
    
    payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content":f"Question: {question}\nContext: {context}\nPreferred Language: {preferred_language}","content": system_prompt},
            {"role": "user", "content": f"Question: {question}\nContext: {context}\nPreferred Language: {preferred_language}"}
        ],
        "max_tokens": 500,
        "temperature": 0.5,
        "n": 1
    }
    
    try:
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()  # Raise an exception for HTTP errors
        result = response.json()
        return result['choices'][0]['message']['content'].strip()
    except requests.exceptions.RequestException as e:
        print(f"Error using OpenAI API: {e}")
        return "Error fetching response from OpenAI API."

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

# Save chat to Excel
# def save_chat_to_excel(chat_data):
#     filename = "chat_history.xlsx"
#     # Check if the file exists
#     if os.path.exists(filename):
#         # Load existing data
#         df = pd.read_excel(filename)
#         # Append new row
#         df = df.append(chat_data, ignore_index=True)
#     else:
#         # Create new DataFrame
#         df = pd.DataFrame([chat_data])
#     # Save to Excel
#     df.to_excel(filename, index=False)

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

    answer = ask_openai(question, context, preferred_language, openai_api_key)

    if preferred_language == "arabic":
        response = answer
    elif preferred_language == "transliteration-hebrew":
        response = transliterate_to_hebrew(answer)
    elif preferred_language == "transliteration-english":
        response = transliterate_to_english(answer)
    else:
        response = "Invalid language option."

    # Save chat to Excel
    chat_data = {
        "Level": level,
        "Week": week,
        "Question": question,
        "Gender": gender,
        "Preferred Language": preferred_language,
        "Context": context,
        "Answer": response
    }
    # save_chat_to_excel(chat_data)

    return jsonify({"answer": response})

# Serve Frontend
@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)