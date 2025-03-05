import os
import json
import re
from pymilvus import connections, Collection
from openai import OpenAI

# Connect to Milvus
try:
    connections.connect(alias="default", host="localhost", port="19530")
    print("✅ Successfully connected to Milvus!")
except Exception as e:
    print(f"❌ Milvus connection failed: {e}")

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Mapping of level to collection name
LEVEL_COLLECTIONS = {
    "beginner": "arabic_beginner",
    "intermediate": "arabic_intermediate",
    "advanced": "arabic_advanced",
    "expert": "arabic_expert"
}

# Helper function to create collection if it does not exist
def create_collection_if_not_exists(collection_name, dim=1536):
    from pymilvus import CollectionSchema, FieldSchema, DataType, utility
    if not utility.has_collection(collection_name):
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=4096),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
            FieldSchema(name="week", dtype=DataType.VARCHAR, max_length=20),
            FieldSchema(name="topic", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="dialect", dtype=DataType.VARCHAR, max_length=50)
        ]
        schema = CollectionSchema(fields, description="Collection for Arabic teaching lessons")
        collection = Collection(collection_name, schema)
        
        # Create index
        index_params = {
            "metric_type": "COSINE",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 1024}
        }
        collection.create_index(field_name="embedding", index_params=index_params)
        
        print(f"Created collection: {collection_name}")
    else:
        collection = Collection(collection_name)
        print(f"Using existing collection: {collection_name}")
    return collection

# Function to extract text from the lesson JSON data
def extract_text_from_lesson(lesson_data):
    text_parts = []
    try:
        # Add lesson information
        if "lesson" in lesson_data:
            text_parts.append(f"Lesson: {lesson_data['lesson']}")
        
        # Extract greetings
        if "greetings" in lesson_data:
            text_parts.append("Greetings:")
            for lang, greetings in lesson_data["greetings"].items():
                text_parts.append(f"{lang.capitalize()} Greetings:")
                text_parts.extend(greetings)
        
        # Extract questions
        if "questions" in lesson_data:
            text_parts.append("\nConversational Questions:")
            for category, translations in lesson_data["questions"].items():
                text_parts.append(f"{category.capitalize()} Question:")
                for lang, question in translations.items():
                    text_parts.append(f"{lang.capitalize()}: {question}")
        
        # Extract examples
        if "examples" in lesson_data:
            text_parts.append("\nExample Sentences:")
            for category, translations in lesson_data["examples"].items():
                text_parts.append(f"{category.capitalize()} Example:")
                for lang, sentence in translations.items():
                    text_parts.append(f"{lang.capitalize()}: {sentence}")
        
        # Extract numbers
        if "numbers" in lesson_data:
            text_parts.append("\nNumbers:")
            for lang, number_dict in lesson_data["numbers"].items():
                text_parts.append(f"{lang.capitalize()} Numbers:")
                for num, word in number_dict.items():
                    text_parts.append(f"{num}: {word}")
    
    except Exception as e:
        print(f"Error extracting text: {e}")
        return ""
    
    return "\n".join(text_parts)

# Function to compute the embedding for a given text using OpenAI
def get_text_embedding(text, model="text-embedding-ada-002"):
    if not text.strip():
        print("Warning: Attempting to embed empty text")
        return [0.0] * 1536  # Return a zero vector if text is empty
    
    try:
        response = openai_client.embeddings.create(
            model=model,
            input=text
        )
        embedding_vector = response.data[0].embedding
        return embedding_vector
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return [0.0] * 1536  # Return a zero vector on error

# Directory containing your JSON files
data_directory = "data_files"  # All your files (e.g., beginner_week01.json) go here

# Regular expression to match filenames like "beginner_week01.json"
file_pattern = re.compile(r'^(beginner|intermediate|advanced|expert)_week(\d{2})\.json$', re.IGNORECASE)

# Loop over each file in the data directory
for filename in os.listdir(data_directory):
    match = file_pattern.match(filename)
    if match:
        level = match.group(1).lower()           # e.g., "beginner"
        week_number = match.group(2)             # e.g., "01"
        week_value = f"week{week_number}"        # e.g., "week01"

        # Get corresponding collection name for this level
        collection_name = LEVEL_COLLECTIONS.get(level)
        if not collection_name:
            print(f"Unknown level in file: {filename}")
            continue

        # Ensure the collection exists (or create it)
        collection = create_collection_if_not_exists(collection_name, dim=1536)

        # Load the JSON file
        file_path = os.path.join(data_directory, filename)
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lesson_data = json.load(f)
        except Exception as e:
            print(f"Error reading {filename}: {e}")
            continue

        # Extract a text summary from the JSON lesson data
        content_text = extract_text_from_lesson(lesson_data)
        
        # Skip if no content was extracted
        if not content_text.strip():
            print(f"No content extracted from {filename}. Skipping.")
            continue

        print(f"Extracted text from {filename}: {content_text[:300]}...")  # Print first 300 characters

        # Compute the embedding vector for the text
        embedding_vector = get_text_embedding(content_text)

        # Determine topics and dialects
        topics = list(lesson_data.get('questions', {}).keys()) if lesson_data.get('questions') else ['general']
        dialects = list(lesson_data.get('greetings', {}).keys()) if lesson_data.get('greetings') else ['multilingual']

        # Prepare lists for insertion 
        # Order must match the schema: [content, embedding, week, topic, dialect]
        contents = [content_text]
        embeddings = [embedding_vector]
        weeks = [week_value]
        topic_list = topics
        dialect_list = dialects

        # Insert the data into Milvus
        entities = [contents, embeddings, weeks, topic_list, dialect_list]
        
        try:
            insert_result = collection.insert(entities)
            collection.flush()
            print(f"Inserted record from {filename} into collection {collection_name} with week {week_value}.")
        except Exception as e:
            print(f"Insertion error for {filename}: {e}")

print("Database population complete!")