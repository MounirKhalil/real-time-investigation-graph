# Quick Testing Guide for Frontend Integration

## Prerequisites

1. **Ensure services are running:**
   - PostgreSQL with pgvector extension
   - Neo4j database
   - API server on port 8058

2. **Environment configured:**
   - `.env` file with all required variables
   - LLM API keys set
   - Database connections configured

---

## Starting the Server

```bash
# Navigate to project root
cd investigator_assistant

# Activate virtual environment (if using one)
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Start API server
python -m agent.api

# Server will start on http://localhost:8058
```

---

## Test Endpoint 1: Q&A Submission

### Using cURL:

```bash
curl -X POST "http://localhost:8058/investigation/submit-qa" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Where were you last Friday evening?",
    "answer": "I was at a restaurant downtown with my friend Mike. We had dinner and talked about business."
  }'
```

### Using Python:

```python
import requests
import json

url = "http://localhost:8058/investigation/submit-qa"
data = {
    "question": "Where were you last Friday evening?",
    "answer": "I was at a restaurant downtown with my friend Mike. We had dinner and talked about business."
}

response = requests.post(url, json=data)
result = response.json()

print("Suggested Questions:")
for i, q in enumerate(result['suggestedQuestions'], 1):
    print(f"{i}. {q}")

print(f"\nGraph URL: {result['graphUrl']}")
```

### Using JavaScript:

```javascript
const response = await fetch('http://localhost:8058/investigation/submit-qa', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    question: "Where were you last Friday evening?",
    answer: "I was at a restaurant downtown with my friend Mike. We had dinner and talked about business."
  })
});

const data = await response.json();
console.log('Suggested Questions:', data.suggestedQuestions);
console.log('Graph URL:', data.graphUrl);
```

### Expected Response:

```json
{
  "suggestedQuestions": [
    "What is the exact name and address of the restaurant downtown?",
    "What is Mike's full name and contact information?",
    "What specific time did you arrive and leave the restaurant?",
    "What specific business matters did you discuss with Mike?",
    "Were there any other people present during your meeting?"
  ],
  "graphUrl": "http://localhost:8058/graph/data?session_id=abc-123-def-456",
  "analysis": "The answer lacks specific details about location, time, and identity. The restaurant is only described as 'downtown' without precise address. Mike's full identity is not provided. The timeframe is vague ('evening'). The business discussion content is unspecified.",
  "session_id": "abc-123-def-456"
}
```

---

## Test Endpoint 2: Analysis Chat

### Using cURL:

```bash
curl -X POST "http://localhost:8058/analysis/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What information do we have about Mike from the interrogation?"
  }'
```

### Using Python:

```python
import requests

url = "http://localhost:8058/analysis/chat"
data = {
    "prompt": "What information do we have about Mike from the interrogation?"
}

response = requests.post(url, json=data)
result = response.json()

print("Assistant's Answer:")
print(result['answer'])
```

### Using JavaScript:

```javascript
const response = await fetch('http://localhost:8058/analysis/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    prompt: "What information do we have about Mike from the interrogation?"
  })
});

const data = await response.json();
console.log('Answer:', data.answer);
```

### Expected Response:

```json
{
  "answer": "Based on the interrogation transcripts, Mike has been mentioned in connection with a restaurant meeting last Friday evening. However, key information is missing:\n\n- Full name is not provided\n- Contact information is unavailable\n- Relationship to the suspect is described only as 'friend'\n- No physical description\n- Business discussion details are unspecified\n\nThis person represents a critical gap in the investigation and requires follow-up questioning."
}
```

---

## Test Endpoint 3: Graph Data

### Using cURL:

```bash
# Get all graph data (limited to 50 nodes by default)
curl "http://localhost:8058/graph/data"

# Get graph data with custom limit
curl "http://localhost:8058/graph/data?limit=20"

# Get graph data for specific session
curl "http://localhost:8058/graph/data?session_id=abc-123-def-456"
```

### Using Python:

```python
import requests

url = "http://localhost:8058/graph/data"
params = {"limit": 30}

response = requests.get(url, params=params)
result = response.json()

print(f"Total Nodes: {len(result['nodes'])}")
print(f"Total Edges: {len(result['edges'])}")

print("\nSample Node:")
if result['nodes']:
    print(result['nodes'][0])

print("\nSample Edge:")
if result['edges']:
    print(result['edges'][0])
```

### Using JavaScript:

```javascript
const response = await fetch('http://localhost:8058/graph/data?limit=30');
const data = await response.json();

console.log(`Total Nodes: ${data.nodes.length}`);
console.log(`Total Edges: ${data.edges.length}`);
console.log('Sample Node:', data.nodes[0]);
console.log('Sample Edge:', data.edges[0]);
```

### Expected Response:

```json
{
  "nodes": [
    {
      "id": "uuid-1",
      "label": "Mike",
      "type": "Person",
      "metadata": {
        "created_at": "2025-01-15T10:30:00Z",
        "summary": "Friend mentioned in restaurant meeting"
      }
    },
    {
      "id": "uuid-2",
      "label": "Downtown Restaurant",
      "type": "Place",
      "metadata": {
        "created_at": "2025-01-15T10:30:00Z",
        "summary": "Location of Friday evening meeting"
      }
    }
  ],
  "edges": [
    {
      "from": "uuid-suspect",
      "to": "uuid-1",
      "label": "had_dinner_with",
      "metadata": {
        "fact": "Suspect had dinner with Mike at a restaurant",
        "created_at": "2025-01-15T10:30:00Z"
      }
    }
  ],
  "metadata": {
    "total_nodes": 2,
    "total_edges": 1,
    "limit": 50,
    "timestamp": "2025-01-15T10:35:00Z"
  }
}
```

---

## Test Endpoint 4: Health Check

### Using cURL:

```bash
curl "http://localhost:8058/health"
```

### Expected Response:

```json
{
  "status": "healthy",
  "database": true,
  "graph_database": true,
  "llm_connection": true,
  "version": "0.1.0",
  "timestamp": "2025-01-15T10:40:00Z"
}
```

---

## Test Scenarios

### Scenario 1: Complete Investigation Flow

```bash
# Step 1: Submit initial Q&A
curl -X POST "http://localhost:8058/investigation/submit-qa" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What did you do on Friday?",
    "answer": "I met with Mike at a restaurant."
  }'

# Step 2: Submit follow-up based on suggested questions
curl -X POST "http://localhost:8058/investigation/submit-qa" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is Mike'\''s full name?",
    "answer": "Mike Johnson."
  }'

# Step 3: Check graph for connections
curl "http://localhost:8058/graph/data?limit=30"

# Step 4: Analyze the investigation
curl -X POST "http://localhost:8058/analysis/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What do we know about the Friday meeting?"
  }'
```

### Scenario 2: Detecting Contradictions

```bash
# Submit first statement
curl -X POST "http://localhost:8058/investigation/submit-qa" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What time did you meet Mike?",
    "answer": "Around 6 PM on Friday."
  }'

# Submit contradictory statement
curl -X POST "http://localhost:8058/investigation/submit-qa" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Can you confirm the meeting time?",
    "answer": "It was Saturday at 8 PM."
  }'

# System should suggest questions about the contradiction
```

---

## Viewing API Documentation

Open in browser: `http://localhost:8058/docs`

This provides:
- Interactive API testing interface
- Full endpoint documentation
- Request/response schemas
- Example requests

---

## Common Issues & Solutions

### Issue 1: "Graph client not initialized"

**Solution:**
- Ensure Neo4j is running
- Check `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` in `.env`
- Restart API server

### Issue 2: "No suggested questions returned"

**Solution:**
- Check LLM API key is valid
- Ensure `LLM_CHOICE` model supports structured output
- Check logs for LLM errors
- System will provide default questions as fallback

### Issue 3: "Empty graph data"

**Solution:**
- Submit some Q&A pairs first to populate the graph
- Graph data is initially empty after fresh start
- Use ingestion pipeline to load existing documents

### Issue 4: CORS errors from frontend

**Solution:**
- API already has `allow_origins=["*"]` configured
- Check browser console for specific error
- Ensure request includes `Content-Type: application/json` header

---

## Performance Monitoring

### Check Response Times:

```bash
# Time Q&A submission
time curl -X POST "http://localhost:8058/investigation/submit-qa" \
  -H "Content-Type: application/json" \
  -d '{"question": "Test?", "answer": "Test answer."}'
```

**Expected times:**
- Q&A submission: 3-15 seconds (depends on Graphiti processing)
- Analysis chat: 2-8 seconds
- Graph data: <1 second (small graphs)

### Check Logs:

```bash
# Watch logs in real-time
tail -f investigator_assistant.log

# Or if running in foreground, observe console output
```

---

## Integration Checklist

- [ ] API server starts without errors
- [ ] Health endpoint returns "healthy"
- [ ] Q&A submission returns 3-5 questions
- [ ] Graph URL is valid and accessible
- [ ] Analysis chat returns relevant answers
- [ ] Graph data endpoint returns nodes and edges
- [ ] CORS allows frontend requests
- [ ] Response times are acceptable (<15s)
- [ ] Error responses are properly formatted
- [ ] Logs show request processing details

---

## Next Steps

Once basic endpoints are working:

1. **Integrate with frontend UI**
   - Connect Investigation Room submit button
   - Wire up Analysis chat interface
   - Implement graph visualization rendering

2. **Add error handling in frontend**
   - Show loading states during processing
   - Display error messages for failed requests
   - Add retry logic for timeout errors

3. **Optimize performance**
   - Add caching for graph data
   - Show progress indicators for long operations
   - Consider pagination for large result sets

4. **Enhance features**
   - Add session persistence
   - Implement conversation history in UI
   - Add entity highlighting in text

---

For more details, see `FRONTEND_INTEGRATION.md`.

