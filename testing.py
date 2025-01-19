import requests

# URL of the Flask server
url_save_user = "http://127.0.0.1:5000/save_user"
url_ask = "http://127.0.0.1:5000/ask"

# Data to be sent to the /save_user endpoint
user_data = {
    "level": "beginner",
    "week": "week01",
    "gender": "male",
    "language": "arabic"
}

# Send POST request to /save_user
response_save_user = requests.post(url_save_user, json=user_data)
print("Response from /save_user:", response_save_user.json())

# Data to be sent to the /ask endpoint
ask_data = {
    "level": "beginner",
    "week": "week01",
    "question": "What is the Arabic word for hello?",
    "gender": "male",
    "language": "arabic"
}

# Send POST request to /ask
response_ask = requests.post(url_ask, json=ask_data)
print("Response from /ask:", response_ask.json())