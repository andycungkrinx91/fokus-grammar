import os
import json
import uuid
import time
import threading
import requests
import edge_tts
import asyncio
import html
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Literal
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles
import traceback # Import traceback for detailed error logging
import google.generativeai as genai
from google.protobuf.json_format import MessageToDict

# === Initialization ===
load_dotenv()

app = FastAPI(title="Fokus Grammar API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULT_MODEL_PROVIDER = os.getenv("DEFAULT_MODEL_PROVIDER", "llama_cpp")
DEFAULT_TTS_VOICE = os.getenv("DEFAULT_TTS_VOICE", "en-US-AnaNeural")
LLAMA_CPP_API_URL = os.getenv("LLAMA_CPP_API_URL", "http://localhost:8000/v1")
LLAMA_MODEL_NAME = os.getenv("LLAMA_MODEL_NAME", "OpenChat-3.5-7B-Qwen-v2.0.Q4_K_M.gguf")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_MODEL_NAME = os.getenv("GOOGLE_MODEL_NAME", "gemini-1.5-flash-latest")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
AUDIO_DIR = os.path.join(BASE_DIR, "data", "audio")
app.mount("/data/audio", StaticFiles(directory=AUDIO_DIR), name="audio")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

QUESTIONS_FILE = os.path.join(DATA_DIR, "grammar_questions.json")
TOPIC_INFO_FILE = os.path.join(DATA_DIR, "grammar_topics.json")

if not os.path.exists(QUESTIONS_FILE):
    with open(QUESTIONS_FILE, "w") as f:
        json.dump([], f)

if not os.path.exists(TOPIC_INFO_FILE):
    with open(TOPIC_INFO_FILE, "w") as f:
        json.dump({}, f)

def load_questions():
    """
    Load all stored grammar questions from JSON file.
    Ensures a list is returned, even if the file is empty, corrupted,
    or contains a non-list JSON type at the root.
    """
    if not os.path.exists(QUESTIONS_FILE):
        try:
            with open(QUESTIONS_FILE, "w") as f:
                json.dump([], f)
            return []
        except Exception as e_init:
            print(f"ERROR: Could not create and initialize {QUESTIONS_FILE}: {e_init}")
            return []

    try:
        with open(QUESTIONS_FILE, 'r') as f:
            content = f.read().strip()
            if not content:
                print(f"INFO: {QUESTIONS_FILE} is empty. Returning an empty list.")
                return []
            
            f.seek(0) 
            data = json.load(f)
            
            if isinstance(data, list):
                return data
            else:
                print(f"WARNING: Data in {QUESTIONS_FILE} was not a list (found type: {type(data)}). Returning an empty list.")
                # Optionally overwrite with '[]'
                # with open(QUESTIONS_FILE, 'w') as wf: json.dump([], wf)
                return []
    except json.JSONDecodeError:
        print(f"ERROR: Could not decode JSON from {QUESTIONS_FILE}. Returning an empty list.")
        return []
    except Exception as e:
        print(f"ERROR: Could not load questions from {QUESTIONS_FILE} due to ({type(e).__name__}: {e}). Returning an empty list.")
        return []

def save_questions(data):
    with open(QUESTIONS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_topic_info():
    try:
        with open(TOPIC_INFO_FILE) as f:
            return json.load(f)
    except:
        return {}

def save_topic_info(data):
    with open(TOPIC_INFO_FILE, "w") as f:
        json.dump(data, f, indent=2)

# === LLM API Call Functions ===
def call_llama_cpp(messages, tools=None, model=LLAMA_MODEL_NAME):
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 8192,
    }
    if tools:
        payload["tools"] = tools
        payload["functions"] = tools # Some models might expect 'functions'
        payload["function_call"] = "auto"

    try:
        res = requests.post(
            f"{LLAMA_CPP_API_URL}/chat/completions",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=300,
        )
        return res.json()
    except Exception as e:
        return {"error": str(e)}

# === Generic function to call generative models ===
def call_generative_model(messages, tools=None, provider: Optional[str] = None):
    """
    Calls the appropriate model provider based on configuration.
    :param messages: The message history to send to the model.
    :param tools: The tools the model can use.
    :param provider: Override the default provider. Can be 'llama_cpp' or 'google_ai'.
    """
    selected_provider = provider or DEFAULT_MODEL_PROVIDER
    
    print(f"INFO: Using model provider: {selected_provider}")
    
    if selected_provider == "google_ai":
        if not GOOGLE_API_KEY:
            return {"error": "GOOGLE_API_KEY is not set in .env file."}
        # Google's tool definition is slightly different, we adapt it here
        google_tools = None
        if tools:
            google_tools = [{"function_declarations": [t["function"] for t in tools]}]
        return call_google_ai(messages, google_tools)
        
    elif selected_provider == "llama_cpp":
        return call_llama_cpp(messages, tools)
        
    else:
        return {"error": f"Invalid model provider '{selected_provider}'. Choose 'llama_cpp' or 'google_ai'."}

# === Google AI Call Function (with adapter) ===
def convert_google_object(obj):
    """
    Recursively converts special Google AI library objects (like MessageMapContainer
    and RepeatedComposite) into standard Python dicts and lists.
    """
    # If the object has an .items() method, treat it as a dictionary.
    if hasattr(obj, 'items'):
        return {key: convert_google_object(value) for key, value in obj.items()}
    
    # If the object is iterable (like a list) but not a string or dict-like.
    elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)):
        return [convert_google_object(item) for item in obj]
    
    # Otherwise, it's a primitive type (str, int, float, bool) and can be returned as is.
    return obj

def call_google_ai(messages, tools=None, model=GOOGLE_MODEL_NAME):
    try:
        # Convert messages to Google's format (this part is correct)
        google_messages = []
        system_prompt = ""
        for msg in messages:
            if msg['role'] == 'system':
                system_prompt += msg['content'] + "\n"
            else:
                google_messages.append({'role': 'user' if msg['role'] == 'user' else 'model', 'parts': [msg['content']]})
        
        if system_prompt and google_messages:
            google_messages[0]['parts'][0] = system_prompt + google_messages[0]['parts'][0]

        gemini_model = genai.GenerativeModel(model_name=model, tools=tools if tools else None)
        response = gemini_model.generate_content(google_messages)
        
        # --- ADAPTER: Convert Google AI response to look like Llama.cpp's response ---
        tool_calls = []
        for part in response.parts:
            if part.function_call:
                serializable_args = convert_google_object(part.function_call.args)
                tool_calls.append({
                    "function": {
                        "name": part.function_call.name,
                        "arguments": json.dumps(serializable_args)
                    }
                })
        
        # Build the final standardized response object
        return {
            "choices": [{
                "message": {
                    "tool_calls": tool_calls
                }
            }]
        }

    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}

# === Text-to-Speech generation function (with enhanced logging) ===
async def synthesize_with_ssml(text_or_ssml: str, filepath: str, voice: str): # Removed default voice, should be decided by caller
    """
    Generates TTS from text or SSML using edge_tts.
    The 'voice' parameter is passed directly to Communicate.
    """
    try:
        communicate = edge_tts.Communicate(text=text_or_ssml, voice=voice)
        await communicate.save(filepath)
    except Exception as e_synth:
        print(f"ERROR: Error in synthesize_with_ssml for '{filepath}' with voice '{voice}': {e_synth}")
        traceback.print_exc() # Ensures full traceback is printed
        raise

def run_async_tts(coro):
    try:
        asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(coro)
        finally:
            loop.close()

def generate_speech(text: str, filepath: str, voice: Optional[str] = None):
    actual_voice = voice or DEFAULT_TTS_VOICE
    ssml_to_send = text
    if not text.strip().lower().startswith("<speak>"):
        escaped_text = html.escape(text)
        ssml_to_send = f'{escaped_text}'
    run_async_tts(synthesize_with_ssml(ssml_to_send, filepath, actual_voice))


def build_ssml_question_options(question_text: str, options: List[str]) -> str:
    """
    Builds a complete SSML string for a question and its options.
    """
    escaped_question_text = html.escape(question_text)
    
    options_ssml_parts = []
    for idx, option_item_text in enumerate(options):
        letter = chr(97 + idx)  # A, B, C...
        escaped_option_text = html.escape(str(option_item_text))
        options_ssml_parts.append(
            f'Option {letter}: {escaped_option_text}"/>'
        )
    
    options_combined_ssml = "".join(options_ssml_parts)

    full_ssml = (
        f'{escaped_question_text}{options_combined_ssml}'
    )
            
    return full_ssml.strip()

def generate_speech_with_options(question: str, options: List[str], filepath: str, voice: Optional[str] = None):
    """
    Thread-safe wrapper for questions with options.
    Calls build_ssml_question_options and then synthesize_with_ssml.
    """
    actual_voice = voice or DEFAULT_TTS_VOICE
    if not actual_voice:
        actual_voice = "en-US-AnaNeural" # Fallback

    ssml_text = build_ssml_question_options(question, options)
    
    try:
        print(f"INFO: generate_speech_with_options: Queued for '{filepath}' with voice '{actual_voice}'")
        asyncio.run(synthesize_with_ssml(ssml_text, filepath, actual_voice))
        print(f"INFO: generate_speech_with_options: TTS task completed for '{filepath}'")
    except RuntimeError:
        print(f"WARN: generate_speech_with_options: RuntimeError for '{filepath}'. Creating new event loop.")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(synthesize_with_ssml(ssml_text, filepath, actual_voice))
            print(f"INFO: generate_speech_with_options: TTS task completed in new loop for '{filepath}'")
        except Exception as e_loop:
            print(f"ERROR: generate_speech_with_options: Error in new event loop for '{filepath}': {e_loop}")
            traceback.print_exc()
        finally:
            loop.close()
    except Exception as e:
        print(f"ERROR: generate_speech_with_options: General error for '{filepath}': {e}")
        traceback.print_exc()

# === Pydantic Schemas for request validation ===
class QuestionGenRequest(BaseModel):
    difficulty: Optional[str] = "medium"
    topic: Optional[str] = ""
    count: Optional[int] = 1
    provider: Optional[Literal['llama_cpp', 'google_ai']] = None

class CheckAnswerItem(BaseModel):
    question_id: str
    answer: str

class CheckAnswerRequest(BaseModel):
    answers: List[CheckAnswerItem]

class TextRequest(BaseModel):
    text: str

class TopicRequest(BaseModel):
    topic: str
    provider: Optional[Literal['llama_cpp', 'google_ai']] = None

class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = DEFAULT_TTS_VOICE


# === API Routes ===
@app.get("/")
def root():
    return {"status": "Fokus Grammar API running"}

@app.get("/api/questions")
def get_questions():
    return load_questions()

@app.post("/api/generate-questions")
def generate_questions_route(req: QuestionGenRequest, background_tasks: BackgroundTasks):
    # ... (tools, count, msg setup remains the same) ...
    tools = [{"type": "function", "function": {
                "name": "generate_grammar_questions",
                "description": "Generate multiple grammar practice questions",
                "parameters": {"type": "object", "properties": {
                        "questions": {"type": "array", "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"}, "question": {"type": "string"},
                                    "options": {"type": "array", "items": {"type": "string"}},
                                    "correct_answer": {"type": "string"}, "explanation_en": {"type": "string"},
                                    "explanation_id": {"type": "string"}, "difficulty": {"type": "string"},
                                    "grammar_topic": {"type": "string"}},
                                "required": ["id", "question", "options", "correct_answer", "explanation_en", "explanation_id", "difficulty", "grammar_topic"]}}}}}}]
    count = max(1, min(req.count or 1, 10))

    msg = [{"role": "system", "content": "You are a helpful assistant that generates English grammar practice questions. Provide explanations in both English and Indonesian languages. /no_think"},
           {"role": "user", "content": f"Generate {count} {req.difficulty} grammar questions about {req.topic or 'any topic'} with explanations in both English and Indonesian. /no_think"}]
    response = call_generative_model(msg, tools, provider=req.provider)

    try:
        if not response or "choices" not in response or not response["choices"] or \
           "message" not in response["choices"][0] or "tool_calls" not in response["choices"][0]["message"] or \
           not response["choices"][0]["message"]["tool_calls"]:
            print(f"ERROR in /api/generate-questions: Unexpected LLM response structure. Response: {response}")
            return {"success": False, "error": "Failed to parse questions from LLM response.", "response": str(response)}

        tool_call = response["choices"][0]["message"]["tool_calls"][0]
        args = json.loads(tool_call["function"]["arguments"])
        
        if "questions" not in args:
            print(f"ERROR in /api/generate-questions: 'questions' key not found in LLM function arguments. Args: {args}")
            return {"success": False, "error": "'questions' not found in LLM arguments.", "response": str(response)}
            
        questions_data = args["questions"]
        all_questions = load_questions()
        processed_questions = []
        for q_data in questions_data: # Removed idx as it wasn't used
            # Ensure ID exists, prefer LLM's ID if it's a UUID, otherwise generate new UUID.
            # Or simply always generate a new UUID as per your last main.py version:
            current_question_uuid = str(uuid.uuid4())
            q_data["id"] = current_question_uuid 
            
            filename = f"{q_data['id']}.mp3"
            filepath = os.path.join(AUDIO_DIR, filename)
            q_data["audio_url"] = f"/data/audio/{filename}"
            
            # Get question and options, providing defaults if missing
            question_text = q_data.get("question", "No question text provided.")
            options_list = q_data.get("options", [])
            if not isinstance(options_list, list): # Ensure options is a list
                options_list = []

            print(f"INFO: [/api/generate-questions] Queuing TTS for question ID {q_data['id']}")
            background_tasks.add_task(
                generate_speech_with_options,
                question_text,
                options_list,
                filepath,
                voice=DEFAULT_TTS_VOICE,
            )
            processed_questions.append(q_data)

        all_questions.extend(processed_questions)
        save_questions(all_questions)

        return {"success": True, "questions": processed_questions}

    except Exception as e:
        print(f"ERROR in /api/generate-questions: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e), "response": str(response)} # str(response) for safety


@app.post("/api/generate-question") # This seems to be a duplicate intent
def generate_question_redirect(req: QuestionGenRequest):
    return generate_questions_route(req) # Call the renamed route function

@app.post("/api/check-answers")
def check_answers(req: CheckAnswerRequest):
    all_qs = load_questions()
    results = []
    # It's better to use the 'id' field you should be generating for questions
    questions_dict = {q["id"]: q for q in all_qs if "id" in q}


    content_for_llm = "Evaluate the following grammar questions and answers:\n\n"
    for item in req.answers:
        q = questions_dict.get(str(item.question_id)) # Ensure question_id is string if IDs are UUIDs
        if not q:
            results.append({
                "question_id": item.question_id,
                "error": "Question not found",
                "is_correct": False
            })
            continue
        
        is_correct = item.answer == q["correct_answer"]
        results.append({
            "question_id": item.question_id,
            "is_correct": is_correct,
            "correct_answer": q["correct_answer"],
            "explanation_en": q.get("explanation_en", ""),
            "explanation_id": q.get("explanation_id", ""),
            "feedback_en": "", # To be filled by LLM if needed
            "feedback_id": ""  # To be filled by LLM if needed
        })
        content_for_llm += (
            f"Q{item.question_id}: {q['question']}\n"
            f"Options: {', '.join(q['options'])}\n"
            f"User Answer: {item.answer}\n"
            f"Correct Answer: {q['correct_answer']}\n"
            f"Status: {'Correct' if is_correct else 'Incorrect'}\n\n"
        )

    return {"success": True, "results": results}

@app.post("/api/check-answer")
def check_answer(req: CheckAnswerItem):
    return check_answers(CheckAnswerRequest(answers=[req]))

@app.post("/api/grammar-topic-info")
def grammar_topic_info(req: TopicRequest):
    topic_info_cache = load_topic_info() # Renamed to avoid conflict
    if req.topic in topic_info_cache:
        return {"success": True, **topic_info_cache[req.topic], "cached": True}

    tools = [
        {
            "type": "function",
            "function": {
                "name": "provide_grammar_info",
                "description": "Provide detailed information about a grammar topic in both English and Indonesian",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "english_content": {"type": "string"},
                        "indonesian_content": {"type": "string"},
                    },
                    "required": ["english_content", "indonesian_content"],
                },
            },
        }
    ]

    messages = [
        {"role": "system", "content": "You are a grammar teacher assistant. When asked a grammar question, always respond by calling the appropriate function. /no_think"},
        {"role": "user", "content": f"Call the function `provide_grammar_info` to explain the topic '{req.topic}' with English and Indonesian explanations. /no_think"},
    ]

    response = call_generative_model(messages, tools, provider=req.provider)

    try:
        message = response["choices"][0]["message"]
        args = None
        if "tool_calls" in message and message["tool_calls"]:
            args = json.loads(message["tool_calls"][0]["function"]["arguments"])
        elif "function_call" in message and message["function_call"]: # For older model compatibility
             args = json.loads(message["function_call"]["arguments"])
        
        if not args:
            print(f"ERROR: No tool_calls or function_call found in LLM response for topic '{req.topic}'. Response: {response}")
            return {"success": False, "error": "Failed to get structured data from LLM.", "response": response}

        topic_info_cache[req.topic] = args
        save_topic_info(topic_info_cache)
        return {"success": True, **args, "cached": False}
    except Exception as e:
        print(f"ERROR in /api/grammar-topic-info: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e), "response": response}

@app.post("/api/tts")
def text_to_speech(req: TTSRequest):
    filename = f"{uuid.uuid4()}.mp3"
    filepath = os.path.join(AUDIO_DIR, filename)
    
    # Use parameters from the request, falling back to defaults in TTSRequest model
    # The generate_speech function also has defaults, but request-specific values should take precedence.
    threading.Thread(target=generate_speech, args=(req.text, filepath, req.voice)).start()
    return {"success": True, "audio_url": f"/data/audio/{filename}"}

@app.get("/api/check-audio/{filename}")
def check_audio(filename: str):
    filepath = os.path.join(AUDIO_DIR, filename)
    exists = os.path.isfile(filepath)
    # Optionally, you could also check if the file size is > 0 if empty files are a concern
    # size = os.path.getsize(filepath) if exists else 0
    # return {"exists": exists, "size": size}
    return {"exists": exists}