# Script to process PDFs and populate the database
# to run the script: python setup_db.py #
import pdfplumber
import sqlite3
import os

# Connect to SQLite database
conn = sqlite3.connect("materials.db")
cursor = conn.cursor()

# Create a table for teaching materials
cursor.execute("""
    CREATE TABLE IF NOT EXISTS materials (
        id INTEGER PRIMARY KEY,
        level TEXT,
        week TEXT,
        content TEXT
    )
""")

# Function to extract text from PDFs
def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
    return text

# Add PDFs to the database
def add_pdf_to_db(level, week, pdf_path):
    content = extract_text_from_pdf(pdf_path)
    if content:
        cursor.execute("INSERT INTO materials (level, week, content) VALUES (?, ?, ?)", (level, week, content))
        conn.commit()
        print(f"Added {pdf_path} to database.")
    else:
        print(f"No content extracted from {pdf_path}")

# Example: Adding PDFs for each level and week
for level in ["beginner", "intermediate", "advanced", "expert"]:
    for week in range(1, 11):
        pdf_path = f"materials/{level}_week{week:02}.pdf"
        if os.path.exists(pdf_path):
            add_pdf_to_db(level, f"week{week:02}", pdf_path)
        else:
            print(f"File {pdf_path} does not exist.")

# Close the database connection
conn.close()
print("PDF content added to the database!")