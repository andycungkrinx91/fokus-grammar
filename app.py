from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
import json
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# LM Studio API configuration
LM_STUDIO_API_URL = "http://127.0.0.1:1234/v1"

# Path to store data
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)
QUESTIONS_FILE = os.path.join(DATA_DIR, "grammar_questions.json")
TOPIC_INFO_FILE = os.path.join(DATA_DIR, "grammar_topics.json")

# Initialize files if they don't exist
if not os.path.exists(QUESTIONS_FILE):
    with open(QUESTIONS_FILE, 'w') as f:
        json.dump([], f)
        
if not os.path.exists(TOPIC_INFO_FILE):
    with open(TOPIC_INFO_FILE, 'w') as f:
        json.dump({}, f)

# Load grammar questions from file
def load_questions():
    try:
        with open(QUESTIONS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

# Save grammar questions to file
def save_questions(questions):
    with open(QUESTIONS_FILE, 'w') as f:
        json.dump(questions, f, indent=2)
        
# Load grammar topic information from file
def load_topic_info():
    try:
        with open(TOPIC_INFO_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}
        
# Save grammar topic information to file
def save_topic_info(topic_info):
    with open(TOPIC_INFO_FILE, 'w') as f:
        json.dump(topic_info, f, indent=2)

# Function to call LM Studio API
def call_lm_studio(messages, tools=None, model="qwen3-8b"):
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": -1
    }
    
    if tools:
        payload["tools"] = tools
    
    try:
        response = requests.post(
            f"{LM_STUDIO_API_URL}/chat/completions",
            headers={"Content-Type": "application/json"},
            json=payload
        )
        return response.json()
    except Exception as e:
        print(f"Error calling LM Studio API: {e}")
        return {"error": str(e)}

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/questions', methods=['GET'])
def get_questions():
    questions = load_questions()
    return jsonify(questions)

@app.route('/api/generate-questions', methods=['POST'])
def generate_questions():
    # Define the tool for generating grammar questions
    tools = [
        {
            "type": "function",
            "function": {
                "name": "generate_grammar_questions",
                "description": "Generate multiple grammar practice questions with multiple choice answers",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "questions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "question": {
                                        "type": "string",
                                        "description": "The grammar question to be answered"
                                    },
                                    "options": {
                                        "type": "array",
                                        "items": {
                                            "type": "string"
                                        },
                                        "description": "Multiple choice options (4 options)"
                                    },
                                    "correct_answer": {
                                        "type": "string",
                                        "description": "The correct answer option"
                                    },
                                    "explanation_en": {
                                        "type": "string",
                                        "description": "Explanation of why the answer is correct and the grammar rule in English"
                                    },
                                    "explanation_id": {
                                        "type": "string",
                                        "description": "Explanation of why the answer is correct and the grammar rule in Indonesian"
                                    },
                                    "difficulty": {
                                        "type": "string",
                                        "enum": ["easy", "medium", "hard"],
                                        "description": "Difficulty level of the question"
                                    },
                                    "grammar_topic": {
                                        "type": "string",
                                        "description": "The specific grammar topic being tested"
                                    }
                                },
                                "required": ["question", "options", "correct_answer", "explanation_en", "explanation_id", "difficulty", "grammar_topic"]
                            },
                            "description": "Array of grammar questions"
                        }
                    },
                    "required": ["questions"]
                }
            }
        }
    ]
    
    # Get parameters from request
    data = request.json
    difficulty = data.get('difficulty', 'medium')
    topic = data.get('topic', '')
    count = data.get('count', 1)
    
    # Limit count to reasonable number to avoid overwhelming the AI
    count = min(max(count, 1), 10)
    
    # Prepare messages for LM Studio
    messages = [
        {"role": "system", "content": "You are a helpful assistant that generates English grammar practice questions. Create challenging but clear questions that test understanding of grammar rules. Provide explanations in both English and Indonesian languages."}, 
        {"role": "user", "content": f"Generate {count} {difficulty} level English grammar questions with explanations in both English and Indonesian"}
    ]
    
    if topic:
        messages[1]["content"] += f" about {topic}"
    
    # Call LM Studio API
    response = call_lm_studio(messages, tools)
    
    # Process the response
    if "choices" in response and response["choices"] and "message" in response["choices"][0]:
        message = response["choices"][0]["message"]
        
        # Check if tool calls are present
        if "tool_calls" in message and message["tool_calls"]:
            tool_call = message["tool_calls"][0]
            if tool_call["function"]["name"] == "generate_grammar_questions":
                try:
                    response_data = json.loads(tool_call["function"]["arguments"])
                    generated_questions = response_data.get("questions", [])
                    
                    if not generated_questions:
                        return jsonify({"success": False, "error": "No questions were generated"})
                    
                    # Load existing questions
                    questions = load_questions()
                    
                    # Add IDs to new questions and save them
                    next_id = len(questions) + 1
                    for i, q in enumerate(generated_questions):
                        q["id"] = next_id + i
                    
                    # Add new questions to existing ones
                    questions.extend(generated_questions)
                    save_questions(questions)
                    
                    return jsonify({"success": True, "questions": generated_questions})
                except json.JSONDecodeError as e:
                    return jsonify({"success": False, "error": f"Invalid JSON from LM Studio: {str(e)}"})
        
        # If no tool calls or other issues
        return jsonify({"success": False, "error": "Failed to generate questions", "response": response})
    
    return jsonify({"success": False, "error": "Invalid response from LM Studio", "response": response})

# Keep the old endpoint for backward compatibility
@app.route('/api/generate-question', methods=['POST'])
def generate_question():
    # Redirect to the new endpoint
    return generate_questions()

@app.route('/api/check-answers', methods=['POST'])
def check_answers():
    data = request.json
    user_answers = data.get('answers', [])
    
    if not user_answers:
        return jsonify({"success": False, "error": "No answers provided"})
    
    # Load all questions
    all_questions = load_questions()
    
    # Prepare results
    results = []
    
    # Define the tool for evaluating answers
    tools = [
        {
            "type": "function",
            "function": {
                "name": "evaluate_grammar_answers",
                "description": "Evaluate multiple grammar question answers and provide feedback",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "evaluations": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "question_id": {
                                        "type": "integer",
                                        "description": "ID of the question being evaluated"
                                    },
                                    "is_correct": {
                                        "type": "boolean",
                                        "description": "Whether the answer is correct"
                                    },
                                    "feedback_en": {
                                        "type": "string",
                                        "description": "Detailed feedback on the answer in English"
                                    },
                                    "feedback_id": {
                                        "type": "string",
                                        "description": "Detailed feedback on the answer in Indonesian"
                                    }
                                },
                                "required": ["question_id", "is_correct", "feedback_en", "feedback_id"]
                            },
                            "description": "Array of evaluations for each answer"
                        }
                    },
                    "required": ["evaluations"]
                }
            }
        }
    ]
    
    # Prepare content for AI evaluation
    content = "Evaluate the following grammar questions and answers:\n\n"
    
    for answer_data in user_answers:
        question_id = answer_data.get('question_id')
        user_answer = answer_data.get('answer')
        
        if not question_id or user_answer is None:
            continue
        
        # Find the question
        question = next((q for q in all_questions if q.get('id') == question_id), None)
        
        if not question:
            continue
        
        # Add to content for AI evaluation
        content += f"Question {question_id}: {question['question']}\n"
        content += f"Options: {', '.join(question['options'])}\n"
        content += f"User's answer: {user_answer}\n"
        content += f"Correct answer: {question['correct_answer']}\n\n"
        
        # Add basic evaluation to results
        is_correct = user_answer == question['correct_answer']
        results.append({
            "question_id": question_id,
            "is_correct": is_correct,
            "correct_answer": question['correct_answer'],
            "explanation_en": question.get('explanation_en', question.get('explanation', '')),
            "explanation_id": question.get('explanation_id', ''),
            "feedback_en": "", # Will be filled by AI in English
            "feedback_id": "" # Will be filled by AI in Indonesian
        })
    
    # If no valid questions were found, return error
    if not results:
        return jsonify({"success": False, "error": "No valid questions found"})
    
    # Prepare messages for LM Studio
    messages = [
        {"role": "system", "content": "You are a helpful assistant that evaluates answers to grammar questions. Provide detailed feedback on why answers are correct or incorrect. Your feedback must be provided in both English and Indonesian languages."}, 
        {"role": "user", "content": content}
    ]
    
    # Call LM Studio API
    response = call_lm_studio(messages, tools)
    
    # Process the response
    if "choices" in response and response["choices"] and "message" in response["choices"][0]:
        message = response["choices"][0]["message"]
        
        # Check if tool calls are present
        if "tool_calls" in message and message["tool_calls"]:
            tool_call = message["tool_calls"][0]
            if tool_call["function"]["name"] == "evaluate_grammar_answers":
                try:
                    evaluation_data = json.loads(tool_call["function"]["arguments"])
                    evaluations = evaluation_data.get("evaluations", [])
                    
                    # Update results with AI feedback
                    for evaluation in evaluations:
                        question_id = evaluation.get("question_id")
                        feedback_en = evaluation.get("feedback_en", "")
                        feedback_id = evaluation.get("feedback_id", "")
                        
                        # Find the corresponding result and update it
                        for result in results:
                            if result["question_id"] == question_id:
                                result["feedback_en"] = feedback_en
                                result["feedback_id"] = feedback_id
                                break
                    
                    return jsonify({"success": True, "results": results})
                except json.JSONDecodeError as e:
                    # If there's an error parsing the JSON, continue with basic evaluation
                    pass
        
        # If no tool calls or parsing error, use the response content as general feedback
        if "content" in message:
            general_feedback = message["content"]
            # Add the general feedback to all results - assume it contains both languages
            for result in results:
                # Try to split feedback into English and Indonesian parts
                if "ENGLISH:" in general_feedback and "INDONESIAN:" in general_feedback:
                    parts = general_feedback.split("INDONESIAN:")
                    english_part = parts[0].replace("ENGLISH:", "").strip()
                    indonesian_part = parts[1].strip()
                    result["feedback_en"] = english_part
                    result["feedback_id"] = indonesian_part
                else:
                    # If not properly formatted, use the same content for both
                    result["feedback_en"] = general_feedback
                    result["feedback_id"] = "Maaf, umpan balik dalam bahasa Indonesia tidak tersedia."  # Sorry, feedback in Indonesian is not available.
    
    # Return results even if AI evaluation failed
    return jsonify({"success": True, "results": results})

# Keep the old endpoint for backward compatibility
@app.route('/api/check-answer', methods=['POST'])
def check_answer():
    data = request.json
    question_id = data.get('question_id')
    user_answer = data.get('answer')
    
    # Convert to format expected by check_answers
    new_data = {
        "answers": [
            {
                "question_id": question_id,
                "answer": user_answer
            }
        ]
    }
    
    # Call the new endpoint
    response = check_answers()
    response_data = response.get_json()
    
    # If successful, extract the first result
    if response_data.get("success") and response_data.get("results"):
        result = response_data["results"][0]
        return jsonify({
            "success": True,
            "is_correct": result["is_correct"],
            "correct_answer": result["correct_answer"],
            "explanation_en": result["explanation_en"],
            "explanation_id": result["explanation_id"],
            "feedback_en": result["feedback_en"],
            "feedback_id": result["feedback_id"]
        })
    
    # Otherwise return the error
    return response

@app.route('/api/grammar-topic-info', methods=['POST'])
def grammar_topic_info():
    data = request.json
    topic = data.get('topic', '')
    
    if not topic:
        return jsonify({"success": False, "error": "No topic provided"})
    
    # Check if we already have this topic in cache
    topic_info = load_topic_info()
    if topic in topic_info:
        print(f"Using cached information for topic: {topic}")
        return jsonify({
            "success": True,
            "english_content": topic_info[topic].get("english_content", ""),
            "indonesian_content": topic_info[topic].get("indonesian_content", ""),
            "cached": True
        })
    
    # If not in cache, generate new information
    print(f"Generating new information for topic: {topic}")
    
    # Define the tool for generating grammar topic information
    tools = [
        {
            "type": "function",
            "function": {
                "name": "provide_grammar_info",
                "description": "Provide detailed information about a grammar topic in both English and Indonesian",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "english_content": {
                            "type": "string",
                            "description": "Detailed explanation of the grammar topic in English, including rules, usage patterns, and examples. For verb tenses, include examples of positive, negative, and question forms. For other topics like articles, prepositions, etc., provide appropriate examples that demonstrate correct usage."
                        },
                        "indonesian_content": {
                            "type": "string",
                            "description": "Detailed explanation of the grammar topic in Indonesian, including rules and usage patterns. IMPORTANT: Do NOT translate the English example sentences to Indonesian, keep them in English to avoid confusion. Instead, explain the rules and concepts in Indonesian while keeping all example sentences in English."
                        }
                    },
                    "required": ["english_content", "indonesian_content"]
                }
            }
        }
    ]
    
    # Prepare messages for LM Studio
    messages = [
        {"role": "system", "content": "You are a helpful assistant that provides detailed information about English grammar topics. Provide comprehensive explanations with examples in both English and Indonesian languages. Format your response with Markdown for better readability, including headings, paragraphs, lists, and emphasis where appropriate. When providing Indonesian explanations, DO NOT translate the English example sentences to Indonesian - keep all examples in English to avoid confusion. Instead, explain the grammar rules and concepts in Indonesian while keeping all example sentences in English."}, 
        {"role": "user", "content": f"Provide detailed information about the grammar topic '{topic}'. Include explanations of the rules, usage patterns, and appropriate examples. For verb tenses, include examples of positive, negative, and question forms. For other topics like articles, prepositions, etc., provide examples that demonstrate correct usage. Make the explanation very detailed and comprehensive."}
    ]
    
    # Call LM Studio API
    response = call_lm_studio(messages, tools)
    
    # Process the response
    if "choices" in response and response["choices"] and "message" in response["choices"][0]:
        message = response["choices"][0]["message"]
        
        # Check if tool calls are present
        if "tool_calls" in message and message["tool_calls"]:
            tool_call = message["tool_calls"][0]
            if tool_call["function"]["name"] == "provide_grammar_info":
                try:
                    grammar_info = json.loads(tool_call["function"]["arguments"])
                    english_content = grammar_info.get("english_content", "")
                    indonesian_content = grammar_info.get("indonesian_content", "")
                    
                    # Process content to ensure it's properly formatted for Markdown
                    # Remove any HTML tags if present
                    english_content = english_content.replace('<div>', '').replace('</div>', '')
                    indonesian_content = indonesian_content.replace('<div>', '').replace('</div>', '')
                    
                    # Save to cache
                    topic_info[topic] = {
                        "english_content": english_content,
                        "indonesian_content": indonesian_content,
                        "timestamp": time.time()
                    }
                    save_topic_info(topic_info)
                    
                    return jsonify({
                        "success": True,
                        "english_content": english_content,
                        "indonesian_content": indonesian_content,
                        "cached": False
                    })
                except json.JSONDecodeError as e:
                    return jsonify({"success": False, "error": f"Invalid JSON from LM Studio: {str(e)}"})
        
        # If no tool calls, try to extract content from the message
        if "content" in message:
            content = message["content"]
            
            # Try to split content into English and Indonesian parts
            if "ENGLISH:" in content and "INDONESIAN:" in content:
                parts = content.split("INDONESIAN:")
                english_content = parts[0].replace('ENGLISH:', '').strip()
                indonesian_content = parts[1].strip()
                
                # Save to cache
                topic_info[topic] = {
                    "english_content": english_content,
                    "indonesian_content": indonesian_content,
                    "timestamp": time.time()
                }
                save_topic_info(topic_info)
                
                return jsonify({
                    "success": True,
                    "english_content": english_content,
                    "indonesian_content": indonesian_content,
                    "cached": False
                })
            else:
                # If not properly formatted, use the same content for both
                english_content = content
                indonesian_content = "Maaf, penjelasan dalam bahasa Indonesia tidak tersedia."  # Sorry, explanation in Indonesian is not available.
                
                # Save to cache
                topic_info[topic] = {
                    "english_content": english_content,
                    "indonesian_content": indonesian_content,
                    "timestamp": time.time()
                }
                save_topic_info(topic_info)
                
                return jsonify({
                    "success": True,
                    "english_content": english_content,
                    "indonesian_content": indonesian_content,
                    "cached": False
                })
    
    return jsonify({"success": False, "error": "Failed to get grammar information"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
