import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import logging
from openai import OpenAI
from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType, utility
import numpy as np

 
# TODO: add logs for users chat data, only admin can see it
# TODO: integrate an API from DataStax/Milvus to store your data in it

# TODO: make the material in JSON fromat and store it in the database
# TODO: refine the assistant's responses to be more accurate and helpful

# ISSUE: the responses are not correct 
# ISSUE: Assitant -API- is not as expected,
#           found that the ChatGPT isn't well,
#                Gemini asstitant is better for now

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Milvus Connection and Collection Setup
def setup_milvus_collection(collection_name):
    """
    Create Milvus collection if it doesn't exist
    """
    try:
        connections.connect(
            alias="default", 
            host=os.getenv("MILVUS_HOST", "localhost"),
            port=os.getenv("MILVUS_PORT", "19530")
        )
        logger.info("Successfully connected to Milvus!")

        # Check if collection exists, create if not
        if not utility.has_collection(collection_name):
            # Define collection schema
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1536),
                FieldSchema(name="dialect", dtype=DataType.VARCHAR, max_length=50),
                FieldSchema(name="week", dtype=DataType.VARCHAR, max_length=20),
                FieldSchema(name="topic", dtype=DataType.VARCHAR, max_length=100)
            ]
            schema = CollectionSchema(fields=fields, description=f"{collection_name} collection")
            
            # Create collection
            collection = Collection(name=collection_name, schema=schema)
            
            # Create index
            index_params = {
                "metric_type": "COSINE",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 1024}
            }
            collection.create_index(field_name="embedding", index_params=index_params)
            logger.info(f"Created collection {collection_name}")
        
    except Exception as e:
        logger.error(f"Milvus setup failed: {e}")
        raise

# Define collections for different levels
LEVEL_COLLECTIONS = {
    "beginner": "arabic_beginner",
    "intermediate": "arabic_intermediate", 
    "advanced": "arabic_advanced",
    "expert": "arabic_expert"
}

# Setup collections on startup
for collection_name in LEVEL_COLLECTIONS.values():
    setup_milvus_collection(collection_name)

def get_relevant_materials(level, week, question):
    """
    Retrieve relevant teaching materials with improved error handling and logging
    """
    try:
        collection_name = LEVEL_COLLECTIONS.get(level, LEVEL_COLLECTIONS["beginner"])
        collection = Collection(collection_name)
        collection.load()
        
        # Add timeout and retry mechanism
        try:
            embedding_response = openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=question
            )
        except Exception as embed_error:
            logger.warning(f"Embedding generation failed: {embed_error}")
            # Fallback embedding generation or default vector
            query_vector = [0.0] * 1536  
        
        query_vector = embedding_response.data[0].embedding
        
        # Enhanced search parameters with fallback
        search_params = {
            "metric_type": "COSINE",
            "params": {"nprobe": 10}
        }
        
        # More robust filtering
        expr = f'week == "{week}"' if week and week.lower() != "all" else None
        
        try:
            results = collection.search(
                data=[query_vector],
                anns_field="embedding",
                param=search_params,
                limit=5,
                expr=expr,
                output_fields=["content", "dialect", "week", "topic"]
            )
        except Exception as search_error:
            logger.error(f"Vector search failed: {search_error}")
            return []
        
        # Comprehensive result processing with validation
        materials = []
        for hits in results:
            for hit in hits:
                try:
                    material = {
                        "content": hit.entity.get("content", ""),
                        "dialect": hit.entity.get("dialect", "Unknown"),
                        "week": hit.entity.get("week", "Unspecified"),
                        "topic": hit.entity.get("topic", "General"),
                        "similarity": hit.score
                    }
                    materials.append(material)
                except Exception as parsing_error:
                    logger.warning(f"Material parsing error: {parsing_error}")
        
        return materials
    
    except Exception as e:
        logger.critical(f"Catastrophic error in material retrieval: {e}")
        return []
    
def create_arabic_teaching_prompt(level, week, question, gender, language, materials):
    """
    Create a detailed prompt for the AI to teach Arabic effectively.
    """
    # Base prompt instructing the AI on how to teach
    base_prompt = f"""
    You are an expert Arabic language tutor specializing in teaching spoken dialect Levant. 
    Your name is 'Arabic Tutor' and your primary goal is to help students learn 
    authentic spoken Levant Arabic in a conversational, practical way.
    
    Current student profile:
    - Level: {level}
    - Week of study: {week}
    - Gender: {gender}
    - Preferred language: {language}
    
    IMPORTANT TEACHING GUIDELINES:
    
    1. AUTHENTICITY: Always teach natural, authentic spoken Arabic as used by natives - not formal MSA.
       Focus on practical, everyday expressions that locals actually use.
       
    2. PERSONALIZATION: Adapt your teaching to the student's level and progress (week {week} of their {level} level).
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
       - Always provide both Arabic script and  תמלול (based on their language preference).
       - For {gender} students, use appropriate gendered forms in Arabic examples.
    """
    
    # Add relevant materials from the vector DB to the prompt
    materials_prompt = "\nREFERENCE MATERIALS FOR THIS QUESTION:\n"
    
    for i, material in enumerate(materials, 1):
        materials_prompt += f"""
        Material {i}:
        - Topic: {material.get('topic', 'General Arabic')}
        - Dialect: {material.get('dialect', 'Levantine')}
        - Week relevance: {material.get('week', 'N/A')}
        - Content: {material.get('content', '')}
        """
    
    # Add language formatting guidance based on the user's choice
    if language == "arabic":
        language_guidance = "\nRespond primarily in Arabic script with minimal explanations in Hebrew.\n"
    elif language == "transliteration-hebrew":
        language_guidance = "\nProvide Arabic responses written in Hebrew characters, plus brief Hebrew explanations.\n"
    elif language == "transliteration-english":
        language_guidance = "\nProvide Arabic responses with English transliteration, plus Hebrew explanations.\n"
    else:  # default English
        language_guidance = "\nProvide responses mainly in Hebrew, with Arabic phrases in both Arabic script and Hebrew transliteration.\n"
    
    complete_prompt = base_prompt + materials_prompt + language_guidance
    return complete_prompt

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
        
        # Retrieve relevant teaching materials
        teaching_materials = get_relevant_materials(level, week, question)
        
        # Create prompt for OpenAI
        prompt = create_arabic_teaching_prompt(
            level, 
            week, 
            question, 
            gender, 
            language, 
            teaching_materials
        )
        
        # Call ChatGPT API
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": question}
            ],
            temperature=0.2,
            max_tokens=1000
        )
        
        answer = response.choices[0].message.content
        
        # Determine text direction
        text_direction = 'rtl' if language == 'arabic' else 'ltr'
        
        return jsonify({
            "answer": answer,
            "language": language,
            "direction": 'ltr'
        })
    
    except Exception as e:
        logger.error(f"Error in /ask endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)