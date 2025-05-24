# Fokus Grammar

A web application for English grammar practice with AI assistance. This application allows users to practice grammar with AI-generated questions and receive AI-powered feedback on their answers.

## Features

- AI-generated grammar practice questions
- Multiple choice question format
- Customizable difficulty levels (easy, medium, hard)
- Option to specify grammar topics
- Detailed feedback and explanations for answers
- Simple and intuitive user interface

## Requirements

- Python 3.9 or higher
- Poetry (for dependency management)
- LM Studio running locally with a compatible model (e.g., qwen3-8b)

## Installation

1. Make sure you have Poetry installed. If not, follow the installation instructions at [Python Poetry](https://python-poetry.org/docs/#installation)

2. Clone this repository or download the source code

3. Install dependencies using Poetry:
   ```
   poetry install
   ```

## Running the Application

1. Start LM Studio and load a compatible model (e.g., qwen3-8b)
2. Make sure the LM Studio API server is running on http://127.0.0.1:1234
3. Run the application using the provided batch file:
   ```
   run.bat
   ```
4. Open your web browser and navigate to http://127.0.0.1:5000

## How to Use

1. Select the difficulty level (easy, medium, or hard)
2. Optionally, specify a grammar topic (e.g., "Past Tense", "Articles", etc.)
3. Click "Generate New Question" to create a new grammar question
4. Select your answer from the multiple-choice options
5. Click "Check Answer" to submit your answer and receive feedback
6. Review the feedback and explanation to improve your understanding

## LM Studio Integration

This application integrates with LM Studio to generate grammar questions and provide feedback. Make sure LM Studio is running with a compatible model before using the application.

## File Structure

- `app.py`: Main Flask application
- `templates/`: HTML templates
- `static/`: Static files (CSS, JavaScript)
- `data/`: Directory for storing grammar questions

## License

This project is licensed under the MIT License - see the LICENSE file for details.
