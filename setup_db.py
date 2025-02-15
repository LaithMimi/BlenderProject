import os
import pdfplumber
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider

# Path to Secure Connect Bundle (Replace with your actual path)
ASTRA_DB_BUNDLE_PATH = "./secure-connect-database_name.zip"

# Configure the database connection
cloud_config = {'secure_connect_bundle': ASTRA_DB_BUNDLE_PATH}
cluster = Cluster(cloud=cloud_config)
session = cluster.connect()

# Set the keyspace
KEYSPACE = "arabic_learning"
session.set_keyspace(KEYSPACE)

# Folder containing PDFs
PDF_FOLDER = "pdfs"  # Update with your actual PDF folder

# Function to create necessary table
def create_tables():
    query = """
    CREATE TABLE IF NOT EXISTS materials (
        id UUID PRIMARY KEY,
        level TEXT,
        week TEXT,
        content TEXT
    );
    """
    session.execute(query)
    print("✅ Table 'materials' created successfully!")

# Function to extract text from a PDF file
def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"❌ Error reading {pdf_path}: {e}")
    return text.strip()

# Function to upload PDFs to Astra DB
def upload_pdfs():
    if not os.path.exists(PDF_FOLDER):
        print(f"❌ Folder '{PDF_FOLDER}' not found!")
        return

    for filename in os.listdir(PDF_FOLDER):
        if filename.endswith(".pdf"):
            pdf_path = os.path.join(PDF_FOLDER, filename)

            # Extract level and week from filename
            parts = filename.replace(".pdf", "").split("_")  # Example: beginner_week01.pdf
            if len(parts) < 2:
                print(f"❌ Skipping invalid file: {filename}")
                continue
            
            level = parts[0].lower()
            week = parts[1].lower()
            
            # Extract text from PDF
            content = extract_text_from_pdf(pdf_path)

            if content:
                query = """
                INSERT INTO materials (id, level, week, content) 
                VALUES (uuid(), %s, %s, %s)
                """
                session.execute(query, (level, week, content))
                print(f"✅ Uploaded {filename} to Astra DB.")
            else:
                print(f"❌ No content extracted from {filename}")

# Run setup
if __name__ == "__main__":
    create_tables()
    upload_pdfs()
