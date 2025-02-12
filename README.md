# BlenderProject

## Description
BlenderProject is a Flask web application designed to assist students in learning Spoken Palestinian Arabic with the help of OpenAI's GPT-4 model. This project integrates various technologies including Flask, SQLite, and the OpenAI API.

## Features
- Fetch learning materials by level and week from an SQLite database.
- Generate responses to user questions using the OpenAI API.
- Transliterate Arabic phrases into Hebrew and English.
- Save user data and chat history.

## Technologies Used
- Flask
- SQLite
- OpenAI API
- Pandas
- Flask-CORS
- Dotenv

## Installation
1. Clone the repository:
    ```shell
    git clone https://github.com/LaithMimi/BlenderProject.git
    ```
2. Navigate to the project directory:
    ```shell
    cd BlenderProject
    ```
3. Install the required dependencies:
    ```shell
    pip install -r requirements.txt
    ```
4. Set up the environment variables by creating a `.env` file and adding your OpenAI API key:
    ```env
    OPENAI_API_KEY=your_openai_api_key
    ```

## Usage
1. Run the Flask application:
    ```shell
    python app.py
    ```
2. Access the application in your web browser at `http://localhost:5000`.

## Routes
- `/ask`: Endpoint to ask a question and get a response from the OpenAI API.
- `/save_user`: Endpoint to save user data.

## Contributing
Feel free to submit issues or pull requests. For major changes, please open an issue first to discuss what you would like to change.

## License
This project is licensed under the MIT License.

## Contact
For any inquiries or questions, please contact LaithMimi.
