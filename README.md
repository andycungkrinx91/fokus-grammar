# Fokus Grammar

A web application for English grammar practice with AI assistance. This application allows users to practice grammar with AI-generated questions and receive AI-powered feedback on their answers.<BR>
This techstack already build with RAG (Retrieval-Augmented Generation)

## Techstack
- Python 3.12 (FastAPI)
- SentenceTransformer Embedding models (all-MiniLM-L6-v2)
- Llama.cpp (Qwen3-4B)
- Google AI Studio (gemini-1.5-flash-latest)
- Qdrant (Vector database)
- Edge-tts (en-US-AnaNeural)

## Features

- AI-generated grammar practice questions
- Multiple choice question format
- Customizable difficulty levels (easy, medium, hard)
- Option to specify grammar topics
- Detailed feedback and explanations for answers
- Text-to-speech functionality for questions
- 

## Requirements

- Docker


## Installation

1. You just need Install docker

2. Clone this repository

3. cd fokus-grammar


## Running the Application

1. copy .env.example to .env
2. Update your .env
3. Download models https://huggingface.co/unsloth/Qwen3-4B-GGUF/resolve/main/Qwen3-4B-UD-Q4_K_XL.gguf?download=true
4. Move model after downloaded under folder data-llama/models/<your_models>
5. If you want use Google AI Studio just go to https://aistudio.google.com/, generate your api key, update your .env DEFAULT_MODEL_PROVIDER="google_ai" and GOOGLE_API_KEY=<your_google_api_key_here>
6. docker network create grammar-network
7. docker compose --compatibility -f docker-compose.yaml up -d --build --force-recreate --remove-orphans (or you can just run ./run.sh)

## How to Use Backend
1. See readme.txt for check test backend

## Llama Integration

This application integrates with Llama or Google AI Studio to generate grammar questions and provide feedback.

## Todo
1. Create frontend from streamlite/vueJs/ReactJs
2. Create audio translate realtime from Bahasa to English or english to Bahasa

## License

This project is licensed under the MIT License - see the LICENSE file for details.
