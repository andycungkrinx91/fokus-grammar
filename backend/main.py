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
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

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
LLAMA_MODEL_NAME = os.getenv("LLAMA_MODEL_NAME", "Qwen3-4B-UD-Q4_K_XL.gguf")
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

# A constant namespace for generating deterministic UUIDs for topics
TOPIC_NAMESPACE = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')

# === Qdrant Client Initialization ===
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
qdrant_client = QdrantClient(url=QDRANT_URL)
embedding_model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
QUESTIONS_COLLECTION_NAME = "grammar_questions"
TOPICS_COLLECTION_NAME = "grammar_topics"

# === Application Startup: Ensure Qdrant Collections Exist ===
@app.on_event("startup")
def startup_event():
    try:
        qdrant_client.recreate_collection(
            collection_name=QUESTIONS_COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=embedding_model.get_sentence_embedding_dimension(),
                distance=models.Distance.COSINE
            ),
        )
        qdrant_client.recreate_collection(
            collection_name=TOPICS_COLLECTION_NAME,
            vectors_config=models.VectorParams(size=4, distance=models.Distance.DOT) # Dummy vector
        )
        print("Qdrant collections checked/created successfully.")
    except Exception as e:
        print(f"ERROR: Could not connect to or set up Qdrant. Please ensure it is running. Error: {e}")

# === LLM API Call Functions ===
def call_llama_cpp(messages, tools=None, model=LLAMA_MODEL_NAME):
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 8192,
    }
    if tools: payload["tools"] = tools
    try:
        res = requests.post(f"{LLAMA_CPP_API_URL}/chat/completions", json=payload, timeout=300)
        res.raise_for_status()
        return res.json()
    except Exception as e: return {"error": str(e)}

def call_generative_model(messages, tools=None, provider: Optional[str] = None):
    selected_provider = provider or DEFAULT_MODEL_PROVIDER
    print(f"INFO: Using model provider: {selected_provider}")
    if selected_provider == "google_ai":
        if not GOOGLE_API_KEY: return {"error": "GOOGLE_API_KEY is not set."}
        google_tools = [{"function_declarations": [t["function"] for t in tools]}] if tools else None
        return call_google_ai(messages, google_tools)
    elif selected_provider == "llama_cpp":
        return call_llama_cpp(messages, tools)
    else: return {"error": f"Invalid model provider '{selected_provider}'."}

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
    if hasattr(obj, 'items'):
        return {key: convert_google_object(value) for key, value in obj.items()}
    elif hasattr(obj, '__iter__') and not isinstance(obj, str):
        return [convert_google_object(item) for item in obj]
    return obj

def call_google_ai(messages, tools=None, model=GOOGLE_MODEL_NAME):
    try:
        google_messages, system_prompt = [], ""
        for msg in messages:
            if msg['role'] == 'system': system_prompt += msg['content'] + "\n"
            else: google_messages.append({'role': 'user' if msg['role'] == 'user' else 'model', 'parts': [msg['content']]})
        if system_prompt and google_messages: google_messages[0]['parts'][0] = system_prompt + google_messages[0]['parts'][0]
        gemini_model = genai.GenerativeModel(model_name=model, tools=tools)
        response = gemini_model.generate_content(google_messages)
        tool_calls = []
        for part in response.parts:
            if part.function_call:
                serializable_args = convert_google_object(part.function_call.args)
                tool_calls.append({"function": {"name": part.function_call.name, "arguments": json.dumps(serializable_args)}})
        return {"choices": [{"message": {"tool_calls": tool_calls}}]}
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}

# === Text-to-Speech generation function (with enhanced logging) ===
async def synthesize_with_ssml(text_or_ssml: str, filepath: str, voice: str):
    """
    The core async function that generates audio from an SSML string.
    """
    try:
        communicate = edge_tts.Communicate(text=text_or_ssml, voice=voice)
        await communicate.save(filepath)
    except Exception as e:
        print(f"ERROR: Failed to synthesize audio for '{filepath}': {e}")
        traceback.print_exc()

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


def build_ssml_question_options(question_text: str, options: List[str], voice_for_lang: str, pitch: str, rate: str) -> str:
    """
    Builds a complete and valid SSML document for a question and its options.
    """
    lang_region = "en-US"
    try:
        if voice_for_lang:
            lang_region = "-".join(voice_for_lang.split('-', 2)[:2])
    except Exception:
        pass

    escaped_question_text = html.escape(question_text)
    options_ssml_parts = []
    for idx, option_item_text in enumerate(options):
        letter = chr(97 + idx)
        escaped_option_text = html.escape(str(option_item_text))
        options_ssml_parts.append(
            f'Option {letter} {escaped_option_text}'
        )
    options_combined_ssml = "".join(options_ssml_parts)

    full_ssml = (
        f''
        f'{options_combined_ssml}'
    )
    return full_ssml

def generate_speech_with_options(question: str, options: List[str], filepath: str, voice: Optional[str] = None, pitch: Optional[str] = None, rate: Optional[str] = None):
    """
    The function called by the background task. It orchestrates the process.
    """
    actual_voice = voice or DEFAULT_TTS_VOICE
    effective_pitch = pitch if pitch is not None else "+0%"
    effective_rate = rate if rate is not None else "+0%"
    ssml_text = build_ssml_question_options(question, options, actual_voice, effective_pitch, effective_rate)
    
    try:
        asyncio.run(synthesize_with_ssml(ssml_text, filepath, actual_voice))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(synthesize_with_ssml(ssml_text, filepath, actual_voice))
        finally:
            loop.close()
    except Exception as e:
        print(f"ERROR in generate_speech_with_options: {e}")
        traceback.print_exc()

# === Unified TTS Task Function ===
def generate_speech_task(text_or_ssml: str, filepath: str, voice: str):
    async def synthesize():
        try:
            communicate = edge_tts.Communicate(text=text_or_ssml, voice=voice)
            await communicate.save(filepath)
        except Exception as e:
            print(f"ERROR synthesizing audio for '{filepath}': {e}")
    try:
        asyncio.run(synthesize())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(synthesize())
        loop.close()

# === Pydantic Schemas ===
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

class TopicRequest(BaseModel):
    topic: str
    provider: Optional[Literal['llama_cpp', 'google_ai']] = None

class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = DEFAULT_TTS_VOICE
    pitch: Optional[str] = "+0%"
    rate: Optional[str] = "+0%"

class SearchRequest(BaseModel):
    text: str
    limit: Optional[int] = 5


# === API Routes ===
@app.get("/")
def root():
    return {"status": "Fokus Grammar API running"}

@app.post("/api/generate-questions")
def generate_questions_route(req: QuestionGenRequest, background_tasks: BackgroundTasks):
    tools = [{"type": "function", "function": {"name": "generate_grammar_questions", "description": "Generate multiple grammar practice questions", "parameters": {"type": "object", "properties": {"questions": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string"}, "question": {"type": "string"}, "options": {"type": "array", "items": {"type": "string"}}, "correct_answer": {"type": "string"}, "explanation_en": {"type": "string"}, "explanation_id": {"type": "string"}}, "required": ["id", "question", "options", "correct_answer", "explanation_en", "explanation_id"]}}}}}}]
    count = max(1, min(req.count or 1, 10))
    msg = [{"role": "system", "content": "You are a helpful assistant that generates English grammar practice multiple-choice questions."}, {"role": "user", "content": f"Generate {count} {req.difficulty} multiple-choice grammar questions about {req.topic or 'any topic'}."}]
    response = call_generative_model(msg, tools, provider=req.provider)
    try:
        if not response.get("choices") or not response["choices"][0].get("message", {}).get("tool_calls"):
            return {"success": False, "error": "Failed to parse questions from LLM response.", "response": str(response)}
        args = json.loads(response["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"])
        if "questions" not in args: return {"success": False, "error": "'questions' not found in LLM arguments."}
        
        points_to_upsert, processed_questions = [], []
        for q_data in args["questions"]:
            question_id = str(uuid.uuid4())
            q_data["id"] = question_id
            filename = f"{question_id}.mp3"
            filepath = os.path.join(AUDIO_DIR, filename)
            q_data["audio_url"] = f"/data/audio/{filename}"
            vector = embedding_model.encode(q_data.get("question", "")).tolist()
            points_to_upsert.append(models.PointStruct(id=question_id, vector=vector, payload=q_data))
            
            # --- SSML BUILDING LOGIC IS NOW HERE, DIRECT AND CLEAR ---
            question_text = html.escape(q_data.get("question", ""))
            options_list = q_data.get("options", [])
            options_ssml_parts = []
            for idx, option_text in enumerate(options_list):
                letter = chr(97 + idx)
                escaped_option = html.escape(str(option_text))
                options_ssml_parts.append(f'Option {letter}{escaped_option}')
            options_ssml = "".join(options_ssml_parts)
            final_ssml = f'{question_text}{options_ssml}'
            
            background_tasks.add_task(generate_speech_task, final_ssml, filepath, DEFAULT_TTS_VOICE)
            processed_questions.append(q_data)

        if points_to_upsert: qdrant_client.upsert(collection_name=QUESTIONS_COLLECTION_NAME, points=points_to_upsert, wait=True)
        return {"success": True, "questions": processed_questions}
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "error": str(e), "response": str(response)}

@app.post("/api/check-answers")
def check_answers(req: CheckAnswerRequest):
    question_ids = [item.question_id for item in req.answers]
    retrieved_points = qdrant_client.retrieve(collection_name=QUESTIONS_COLLECTION_NAME, ids=question_ids, with_payload=True)
    questions_dict = {point.id: point.payload for point in retrieved_points}
    results = []
    for item in req.answers:
        q_payload = questions_dict.get(item.question_id)
        if not q_payload:
            results.append({"question_id": item.question_id, "error": "Question not found", "is_correct": False})
            continue
        is_correct = item.answer == q_payload.get("correct_answer")
        results.append({"question_id": item.question_id, "is_correct": is_correct, "correct_answer": q_payload.get("correct_answer"), "explanation_en": q_payload.get("explanation_en", "")})
    return {"success": True, "results": results}

@app.post("/api/check-answer")
def check_answer(req: CheckAnswerItem):
    return check_answers(CheckAnswerRequest(answers=[req]))

@app.post("/api/grammar-topic-info")
def grammar_topic_info(req: TopicRequest):
    topic_id = str(uuid.uuid5(TOPIC_NAMESPACE, req.topic.lower()))
    # Checks for the topic in the Qdrant collection first
    retrieved_points = qdrant_client.retrieve(
        collection_name=TOPICS_COLLECTION_NAME,
        ids=[topic_id],
        with_payload=True
    )
    if retrieved_points:
        return {"success": True, **retrieved_points[0].payload, "cached": True}

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
       # Upsert the new topic info into Qdrant
        qdrant_client.upsert(
            collection_name=TOPICS_COLLECTION_NAME,
            points=[
                models.PointStruct(
                    id=topic_id,
                    # We use a dummy vector since we're just storing key-value data here
                    vector=[0.1, 0.2, 0.3, 0.4], 
                    payload=args
                )
            ],
            wait=True
        )

        return {"success": True, **args, "cached": False}

    except Exception as e:
        print(f"ERROR in /api/grammar-topic-info: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e), "response": response}

@app.post("/api/tts")
def text_to_speech(req: TTSRequest):
    filename = f"{uuid.uuid4()}.mp3"
    filepath = os.path.join(AUDIO_DIR, filename)
    escaped_text = html.escape(req.text)
    final_ssml = f'{escaped_text}'
    threading.Thread(target=generate_speech_task, args=(final_ssml, filepath, req.voice)).start()
    return {"success": True, "audio_url": f"/data/audio/{filename}"}

@app.get("/api/check-audio/{filename}")
def check_audio(filename: str):
    filepath = os.path.join(AUDIO_DIR, filename)
    exists = os.path.isfile(filepath)
    return {"exists": exists}

#== Utility Functions Qdrant===
@app.get("/api/questions/{question_id}")
def get_question_by_id(question_id: str):
    retrieved_points = qdrant_client.retrieve(
        collection_name=QUESTIONS_COLLECTION_NAME,
        ids=[question_id],
        with_payload=True
    )
    if not retrieved_points:
        return {"success": False, "error": "Question not found"}
    return {"success": True, "question": retrieved_points[0].payload}

@app.post("/api/questions/search")
def search_similar_questions(req: SearchRequest):
    query_vector = embedding_model.encode(req.text).tolist()
    search_results = qdrant_client.search(collection_name=QUESTIONS_COLLECTION_NAME, query_vector=query_vector, limit=req.limit, with_payload=True)
    hits = [{"score": hit.score, "data": hit.payload} for hit in search_results]
    return {"success": True, "results": hits}
