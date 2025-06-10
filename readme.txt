# === 1. Root Endpoint === (OK)
# Simple health check to verify API is running
curl -X GET "http://localhost:5000/"

# === 2. Get question === (OK)
# Retrieve all stored grammar questions
curl -X GET "http://localhost:5000/api/questions/cf8f6aac-f843-41b3-826e-85ae8a25071c"

# === 3. Generate Questions === (OK)
# Generate new grammar questions (3 medium difficulty about tenses)
curl -X POST "http://localhost:5000/api/generate-questions" \
  -H "Content-Type: application/json" \
  -d '{"difficulty": "medium", "topic": "tenses", "count": 1, "provider": "llama_cpp"}'
curl -X POST "http://localhost:5000/api/generate-questions" \
  -H "Content-Type: application/json" \
  -d '{"difficulty": "medium", "topic": "tenses", "count": 1, "provider": "google_ai"}'

# === 4. Check Answers === (OK)
# Check multiple answers (replace question_ids with actual IDs from your database)
curl -X POST "http://localhost:5000/api/check-answers" \
  -H "Content-Type: application/json" \
  -d '{
    "answers": [
      {"question_id": "abc123", "answer": "was playing"},
      {"question_id": "def456", "answer": "bla bla bla"}
    ]
  }'

# Check single answer (OK)
curl -X POST "http://localhost:5000/api/check-answer" \
  -H "Content-Type: application/json" \
  -d '{"question_id": "cf8f6aac-f843-41b3-826e-85ae8a25071c", "answer": "was playing"}'

# === 5. Grammar Topic Info === (OK)
# Get explanation about a grammar topic (caches response)
curl -X POST "http://localhost:5000/api/grammar-topic-info" \
  -H "Content-Type: application/json" \
  -d '{"topic": "tenses", "provider": "llama_cpp"}'
curl -X POST "http://localhost:5000/api/grammar-topic-info" \
  -H "Content-Type: application/json" \
  -d '{"topic": "tenses", "provider": "google_ai"}'

# === 6. Text-to-Speech === (OK)
# Convert text to speech (returns audio URL)
curl -X POST "http://localhost:5000/api/tts" \
-H "Content-Type: application/json" \
-d '{"text": "Two Omaha men, Jesse Pursell and Sam Corbino, began a search in 1967 that led to the discovery of the Steamboat Bertrand. The Missouri River had changed course over time, leaving the forgotten wreck in the middle of a Nebraska cornfield. Operating under a Federal contract, the pair successfully completed the excavation of the boat and its cargo in 1969. Much of the material is on display in the visitor center of DeSoto National Wildlife Refuge maintained by the U.S. Fish and Wildlife Service."}'

# === 7. Check Audio File === (OK)
# Verify if audio file exists (use filename from TTS response)
curl -X GET "http://localhost:5000/api/check-audio/cf8f6aac-f843-41b3-826e-85ae8a25071c.mp3"

# === 8.  Search Question === (OK)
# Provider test
curl -X POST "http://localhost:5000/api/questions/search" \
-H "Content-Type: application/json" \
-d '{
    "text": "Before my friends arrived, I had been playing video games for three hours.",
    "limit": 1
}'
