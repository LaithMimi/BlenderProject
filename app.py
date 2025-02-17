from flask import Flask, request, jsonify, render_template, g
import sqlite3
import os
import requests
from flask_cors import CORS
from dotenv import load_dotenv
import logging
from typing import Optional, Dict  # Removed 'Any'
from datetime import datetime

# Initialize Flask app and logging
app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Constants
DATABASE = "materials.db"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = "gpt-4"

class DatabaseManager:
    @staticmethod
    def get_db():
        """Retrieve or create a database connection for this request."""
        if 'db' not in g:
            g.db = sqlite3.connect(DATABASE)
            g.db.row_factory = sqlite3.Row
        return g.db

    @staticmethod
    def close_db(e=None):
        """Close the database connection at the end of the request."""
        db = g.pop('db', None)
        if db is not None:
            db.close()

    @staticmethod
    def get_content_by_level_week(level: str, week: str) -> Optional[str]:
        """
        Fetch the 'content' field from the 'materials' table based on the provided level and week.
        Returns None if no matching record is found or if there's a DB error.
        """
        try:
            db = DatabaseManager.get_db()
            cursor = db.cursor()
            cursor.execute(
                "SELECT content FROM materials WHERE level = ? AND week = ?",
                (level, week)
            )
            result = cursor.fetchone()
            return result[0] if result else None
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            return None

class OpenAIManager:
    @staticmethod
    def create_system_prompt() -> str:
        """
        Returns an improved system prompt that outlines how the AI should behave
        as a concise, interactive Arabic tutor for Hebrew-speaking students.
        """
        return (
            "You are an interactive Spoken Palestinian dialect Arabic tutor"
            "for Hebrew-speaking students. "
            "do not use # or any other special characters in the response and after every sentence add a new line "
            "Use the user's preferred language for instructions and teach ONLYspoken Palestinian dialect"
            "transliterations and pronunciation. Offer quizzes or dialogues only if requested "
            "Gently correct mistakes with brief explanations. Base teaching ONLY on the given material"
            "Politely note if content is unavailable and maintain a supportive, engaging tone."
        )

    @staticmethod
    def ask_openai(question: str, context: str, preferred_language: str) -> str:
        """Send a message to the OpenAI API and return the assistant's response."""
        if not OPENAI_API_KEY:
            logger.error("OpenAI API key not found")
            return "Configuration error: OpenAI API key not set"

        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": OpenAIManager.create_system_prompt()},
                {
                    "role": "user",
                    "content": (
                        f"Question: {question}\n"
                        f"Context: {context}\n"
                        f"Preferred Language: {preferred_language}"
                    )
                }
            ],
            "max_tokens": 800,
            "temperature": 0.8
        }

        try:
            response = requests.post(OPENAI_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content'].strip()
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenAI API error: {e}")
            return "Error: Unable to get response from OpenAI"

class TransliterationManager:
    """Handles transliteration from Arabic to Hebrew or English."""
    ARABIC_TO_HEBREW = {
        "ا": "א", "ب": "ב", "ت": "ת", "ث": "ת'", "ج": "ג", "ح": "ח", "خ": "כ'",
        "د": "ד", "ذ": "ד'", "ر": "ר", "ز": "ז", "س": "ס", "ش": "ש", "ص": "צ",
        "ض": "צ'", "ط": "ט", "ظ": "ט'", "ع": "ע", "غ": "ע'", "ف": "פ", "ق": "ק",
        "ك": "כ", "ل": "ל", "م": "מ", "ن": "נ", "ه": "ה", "و": "ו", "ي": "י",
        "ء": "'", "ئ": "'", "ى": "י", "ة": "ה"
    }

    ARABIC_TO_ENGLISH = {
        "ا": "a", "ب": "b", "ت": "t", "ث": "th", "ج": "j", "ح": "h", "خ": "kh",
        "د": "d", "ذ": "dh", "ر": "r", "ز": "z", "س": "s", "ش": "sh", "ص": "s",
        "ض": "d", "ط": "t", "ظ": "th", "ع": "a'", "غ": "gh", "ف": "f", "ق": "q",
        "ك": "k", "ل": "l", "م": "m", "ن": "n", "ه": "h", "و": "w", "ي": "y",
        "ء": "'", "ئ": "i", "ى": "a", "ة": "h"
    }

    @staticmethod
    def transliterate(text: str, rules: Dict[str, str]) -> str:
        """Transliterate the given text based on the provided rules dictionary."""
        return ''.join(rules.get(char, char) for char in text)

# Register the database close function
app.teardown_appcontext(DatabaseManager.close_db)

@app.route("/save_user", methods=["POST"])
def save_user():
    """
    Handle user data, attach a timestamp, and return a success JSON response.
    """
    try:
        user_data = request.get_json()
        if not user_data:
            return jsonify({"error": "No data provided"}), 400

        user_data['timestamp'] = datetime.utcnow().isoformat()

        return jsonify({
            "status": "success",
            "message": "User data received",
            "data": user_data
        })
    except Exception as e:
        logger.error(f"Error saving user data: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/ask", methods=["POST"])
def ask():
    """
    Main route for handling user questions:
      1. Validates input
      2. Fetches context from DB
      3. Queries OpenAI
      4. Transliterates response if necessary
      5. Returns JSON result
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        required_fields = ["level", "week", "question", "gender", "language"]
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400

        # Get content for the specified level and week
        context = DatabaseManager.get_content_by_level_week(data["level"], data["week"])
        if not context:
            return jsonify({"error": "No content found for the selected week"}), 404

        # Get response from OpenAI
        answer = OpenAIManager.ask_openai(data["question"], context, data["language"])

        # Handle transliteration based on preferred language
        if data["language"] == "arabic":
            response = answer
        elif data["language"] == "transliteration-hebrew":
            response = TransliterationManager.transliterate(
                answer, TransliterationManager.ARABIC_TO_HEBREW
            )
        elif data["language"] == "transliteration-english":
            response = TransliterationManager.transliterate(
                answer, TransliterationManager.ARABIC_TO_ENGLISH
            )
        else:
            return jsonify({"error": "Invalid language option"}), 400

        return jsonify({
            "status": "success",
            "answer": response,
            "metadata": {
                "level": data["level"],
                "week": data["week"],
                "timestamp": datetime.utcnow().isoformat()
            }
        })

    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/")
def home():
    """
    Render the main index page
    """
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
