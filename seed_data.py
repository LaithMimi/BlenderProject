import os
import json
from flask import Flask
from flask_pymongo import PyMongo
from dotenv import load_dotenv

# 1) Load environment variables from .env
load_dotenv()

app = Flask(__name__)

# 2) Set up MongoDB connection
app.config["MONGO_URI"] = os.getenv("MONGO_URI")
mongo = PyMongo(app)

def seed_database():
    """Insert each JSON file in data_files/ as a separate doc in the 'materials' collection."""
    materials_coll = mongo.db["materials"]
    
    # (Optional) Clear existing data in the collection first:
    materials_coll.delete_many({})
    
    # 3) Loop over all .json files in data_files/
    data_dir = "data_files"
    for filename in os.listdir(data_dir):
        if filename.endswith(".json"):
            filepath = os.path.join(data_dir, filename)
            print(f"Reading file: {filepath}")
            
            # 4) Load the JSON
            with open(filepath, "r", encoding="utf-8") as f:
                # If each file has just one JSON object, .load() returns a dict
                # If it has multiple, you may need .load() as a list or parse differently
                data = json.load(f)

            # 5) Insert into Mongo
            result = materials_coll.insert_one(data)
            print(f"Inserted {filename} with _id: {result.inserted_id}")

    print("All JSON files have been inserted into the 'materials' collection.")

if __name__ == "__main__":
    with app.app_context():
        seed_database()
