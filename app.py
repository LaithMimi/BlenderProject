import os
import logging
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import openai
from flask_pymongo import PyMongo


load_dotenv()

app = Flask(__name__)
CORS(app)

# -------------------------------------------------------------------
# 1) Setup logging
# -------------------------------------------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# -------------------------------------------------------------------
# 2) Setup OpenAI
# -------------------------------------------------------------------
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -------------------------------------------------------------------
# 3) Configure MongoDB
# -------------------------------------------------------------------
app.config["MONGO_URI"] = os.getenv("MONGO_URI")
mongo = PyMongo(app)

# my JSON files have been inserted into a collection named 'materials'
materials_coll = mongo.db["materials"]

# -------------------------------------------------------------------
# 4) Helper function: get_relevant_materials
# -------------------------------------------------------------------
def get_relevant_materials(level, week, question):
    """
    Retrieve relevant teaching materials from the MongoDB 'materials' collection
    based on the user's level and week. 
    """

    # EXAMPLE APPROACH:
    # Each JSON doc has a "lesson" field, like "Beginner - Week 1", "Beginner - Week 2", etc.
    # We'll build that string from level + week. 

    # Suppose the user passes: level="beginner", week="week01"
    # Then my doc might have "lesson": "Beginner - Week 1"
    # We'll parse out the numeric part from "week01" => "1"
    # Or just do a simple guess: "Beginner - Week 01"

    # Turn "beginner" -> "Beginner"
    level_str = level.capitalize()  # e.g. 'Beginner'
   
    # We'll do a quick parse for digits:
    week_number = ''.join(filter(str.isdigit, week)) or '1'  # default to '1' if no digit found
   
    # Build the lesson key
    lesson_key = f"{level_str} - Week {int(week_number)}"

    # Query the DB for a single doc with "lesson": "Beginner - Week 1"
    doc = materials_coll.find_one({"lesson": lesson_key})
    if doc:
        # Convert the _id to a string for convenience
        doc["_id"] = str(doc["_id"])
        # Return as a list, so the calling code can iterate
        return [doc]
    else:
        # If not found, just return an empty list
        logger.info(f"No document found for lesson '{lesson_key}'. Returning empty list.")
        return []

# -------------------------------------------------------------------
# 5) Prompt-building function 
# -------------------------------------------------------------------
def create_arabic_teaching_prompt(level, week, question, gender, language, materials):
    """
    Create a detailed prompt for the AI to teach Arabic effectively.
    """
    # Base prompt
    base_prompt = f"""
    You are an expert Arabic language tutor specializing in teaching spoken dialect Levant. 
    Your name is 'Arabic Tutor' and your primary goal is to help students learn 
    authentic spoken Levant Arabic in a conversational, practical way, use only the given information to respond.
    
    Current student profile:
    - Level: {level}
    - Week of study: {week}
    - Gender: {gender}
    - Preferred language: {language}
    
    IMPORTANT TEACHING GUIDELINES:
    
    1. AUTHENTICITY: Always teach natural, authentic spoken Arabic as used by natives - not formal MSA.
       Focus on practical, everyday expressions that locals actually use.
       
    2. PERSONALIZATION: Adapt teaching to the student's level and progress (week {week} of their {level} level).
       For beginners, use more of their preferred language. For advanced students, use more Hebrew.
       
    3. CULTURAL CONTEXT: Include cultural notes that help explain why certain phrases are used in specific contexts.
       
    4. TEACHING APPROACH:
       - For grammar questions: Explain simply with examples, not abstract rules.
       - For vocabulary: Provide example sentences showing practical usage.
       - For pronunciation: Use phonetic transliteration when helpful.
       - For practice: Create mini-dialogues the student can use in real life.
       
    5. RESPONSE FORMAT:
       - If the student writes in their native language, respond primarily in that language with Arabic examples.
       - If the student attempts to write in Arabic, praise their effort and gently correct if needed.
       - Always provide both Arabic script and תמלול (based on their language preference).
       - For {gender} students, use appropriate gendered forms in Arabic examples.
    """

    # Add reference materials
    materials_prompt = "\nREFERENCE MATERIALS FOR THIS QUESTION THAT YOUR RESPONSES SHOULD OBLY RELY ON:\n"

    # 'materials' is a list of docs, typically one doc if matched by lesson
    for i, mat in enumerate(materials, 1):
        materials_prompt += f"Material {i}: {mat}\n"

    # Add language formatting guidance
    if language == "arabic":
        language_guidance = "\nRespond primarily in Arabic script with minimal explanations in Hebrew.\n"
    elif language == "transliteration-hebrew":
        language_guidance = "\nProvide Arabic responses written in Hebrew characters, plus brief Hebrew explanations.\n"
    elif language == "transliteration-english":
        language_guidance = "\nProvide Arabic responses with English transliteration, plus Hebrew explanations.\n"
    else:
        language_guidance = "\nProvide responses mainly in Hebrew, with Arabic phrases in both Arabic script and Hebrew transliteration.\n"

    complete_prompt = base_prompt + materials_prompt + language_guidance
    return complete_prompt

# -------------------------------------------------------------------
# 6) /ask endpoint
# -------------------------------------------------------------------
@app.route('/ask', methods=['POST'])
def ask():
    try:
        data = request.json
        
        # Extract request parameters
        level = data.get('level', 'beginner')
        week = data.get('week', 'week01')
        question = data.get('question', '')
        gender = data.get('gender', 'male')
        language = data.get('language', 'english')
        
        # Retrieve relevant teaching materials from Mongo
        teaching_materials = get_relevant_materials(level, week, question)
       
        # 2) **DEBUG PRINT** the retrieved materials
        print("\n--- DEBUG: Extracted Materials ---")
        print(teaching_materials)
        print("---------------------------------\n")
       
        # Build the prompt for OpenAI
        prompt = create_arabic_teaching_prompt(
            level, 
            week, 
            question, 
            gender, 
            language, 
            teaching_materials
        )
        
        # Call ChatGPT (OpenAI) API
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": question}
            ],
            temperature=0.0,
            max_tokens=1000
        )
        
        answer = response.choices[0].message.content
        
        # Determine text direction
        text_direction = 'rtl' if language == 'arabic' else 'ltr'
        
        return jsonify({
            "answer": answer,
            "language": language,
            "direction": text_direction
        })
    
    except Exception as e:
        logger.error(f"Error in /ask endpoint: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# -------------------------------------------------------------------
# 7) Home route
# -------------------------------------------------------------------
@app.route('/')
def home():
    return render_template('index.html')

# -------------------------------------------------------------------
# 8) Run the Flask app
# -------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
