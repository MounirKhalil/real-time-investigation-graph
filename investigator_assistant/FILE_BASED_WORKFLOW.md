# File-Based Investigation Workflow

## Overview

This system now runs as an **always-on server** that:
1. Receives Q&A pairs from the frontend
2. Appends them to `documents/session.md` file
3. Regenerates the knowledge graph from the entire file
4. Generates a PNG visualization of the graph
5. Returns suggested questions and the PNG URL

---

## Quick Start

### 1. Install Dependencies

```bash
# Install new dependencies for graph visualization
pip install networkx==3.2.1 matplotlib==3.8.2

# Or install all dependencies
pip install -r requirements.txt
```

### 2. Start the Server (Always Running)

```bash
# Start the API server
python -m agent.api

# Server will run on http://localhost:8058
# It stays running and listens for Q&A submissions
```

### 3. Submit Q&A from Frontend

```bash
# Example: Submit a Q&A pair
curl -X POST "http://localhost:8058/investigation/submit-qa" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Michael, where were you on the evening of June 12th around 8 p.m.?",
    "answer": "I was at Jack'\''s Diner on 5th Street."
  }'
```

### 4. Response with PNG URL

```json
{
  "suggestedQuestions": [
    "What time did you arrive at Jack's Diner?",
    "How long did you stay at Jack's Diner?",
    "Who was with you at Jack's Diner?",
    "What did you do after leaving Jack's Diner?",
    "Can anyone verify you were at Jack's Diner?"
  ],
  "graphUrl": "http://localhost:8058/static/graphs/graph_20250115_103045.png",
  "analysis": "The answer provides a specific location but lacks temporal details...",
  "session_id": "abc-123-def-456"
}
```

---

## How It Works

### Workflow Diagram:

```
Frontend sends Q&A
    ↓
POST /investigation/submit-qa
    ↓
┌─────────────────────────────────────────────┐
│ Step 1: Append to session.md                │
│                                             │
│  Before:                                    │
│  Investigator: Please state your name...   │
│  Suspect: My name is Michael Turner.       │
│                                             │
│  After:                                     │
│  Investigator: Please state your name...   │
│  Suspect: My name is Michael Turner.       │
│                                             │
│  Investigator: Where were you on June 12?  │
│  Suspect: I was at Jack's Diner...         │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│ Step 2: Regenerate Knowledge Graph          │
│  - Read entire session.md file              │
│  - Extract entities (people, places, etc.)  │
│  - Build relationships in Neo4j             │
│  - Takes 5-15 seconds                       │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│ Step 3: Generate PNG Visualization          │
│  - Query Neo4j for entities and edges       │
│  - Use networkx + matplotlib                │
│  - Save to static/graphs/graph_TIMESTAMP.png│
│  - Takes 1-2 seconds                        │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│ Step 4: Analyze for Suggested Questions     │
│  - Run AI agent analysis                    │
│  - Find gaps and contradictions             │
│  - Generate 3-5 follow-up questions         │
│  - Takes 2-8 seconds                        │
└─────────────────────────────────────────────┘
    ↓
Return: {suggestedQuestions, graphUrl (PNG)}
```

---

## File Structure

```
investigator_assistant/
├── documents/
│   └── session.md          ← Q&A transcript (appended each time)
├── static/
│   └── graphs/
│       ├── graph_20250115_103045.png  ← Generated graphs
│       ├── graph_20250115_103120.png
│       └── graph_20250115_103245.png
├── agent/
│   ├── api.py              ← Main API server
│   ├── investigation_api.py ← Q&A submission endpoint
│   └── file_based_storage.py ← File append & graph generation
└── ingestion/
    └── ingest.py           ← Called internally to regenerate graph
```

---

## session.md Format

The file follows this format:

```markdown
Investigator: [Question 1]
Suspect: [Answer 1]

Investigator: [Question 2]
Suspect: [Answer 2]

Investigator: [Question 3]
Suspect: [Answer 3]
```

### Example:

```markdown
Investigator: Please state your name for the record.
Suspect: My name is Michael Turner.

Investigator: Michael, where were you on the evening of June 12th around 8 p.m.?
Suspect: I was at Jack's Diner on 5th Street.

Investigator: What time did you arrive at Jack's Diner?
Suspect: Around 7:30 PM, maybe a bit earlier.
```

---

## API Endpoints

### 1. Submit Q&A (Main Endpoint)

```
POST /investigation/submit-qa
```

**Request:**
```json
{
  "question": "Where were you on June 12th?",
  "answer": "I was at Jack's Diner on 5th Street."
}
```

**Response:**
```json
{
  "suggestedQuestions": [
    "What time did you arrive at Jack's Diner?",
    "Who were you with at Jack's Diner?",
    "How long did you stay?",
    "What did you order?",
    "Can anyone confirm you were there?"
  ],
  "graphUrl": "http://localhost:8058/static/graphs/graph_20250115_103045.png",
  "analysis": "The answer provides location but lacks temporal details...",
  "session_id": "abc-123"
}
```

### 2. View Graph PNG

```
GET /static/graphs/graph_TIMESTAMP.png
```

Returns the PNG image directly in the browser or can be embedded in `<img>` tag:

```html
<img src="http://localhost:8058/static/graphs/graph_20250115_103045.png" 
     alt="Knowledge Graph" />
```

### 3. Health Check

```
GET /health
```

Check if server is running and databases are connected.

---

## Performance

### Expected Processing Times:

| Step | Time | Notes |
|------|------|-------|
| Append to file | <10ms | Very fast |
| Graph regeneration | 5-15s | Depends on file size |
| PNG generation | 1-2s | Depends on graph size |
| Question analysis | 2-8s | LLM processing |
| **Total** | **8-25s** | Per Q&A submission |

### Optimization Tips:

1. **Background processing**: Consider making graph regeneration async
2. **Caching**: Only regenerate if file changed significantly
3. **Incremental updates**: Update graph instead of full regeneration
4. **Smaller chunks**: Process only recent Q&As for analysis

---

## Example Frontend Integration

### HTML + JavaScript

```html
<!DOCTYPE html>
<html>
<head>
    <title>Investigation Room</title>
</head>
<body>
    <h1>Investigation Room</h1>
    
    <!-- Q&A Form -->
    <div id="qa-form">
        <label>Question:</label>
        <input type="text" id="question" placeholder="Enter your question" />
        
        <label>Answer:</label>
        <textarea id="answer" placeholder="Enter suspect's answer"></textarea>
        
        <button onclick="submitQA()">Submit</button>
    </div>
    
    <!-- Suggested Questions -->
    <div id="suggested-questions">
        <h2>Suggested Follow-up Questions:</h2>
        <ul id="questions-list"></ul>
    </div>
    
    <!-- Graph Visualization -->
    <div id="graph-visualization">
        <h2>Knowledge Graph:</h2>
        <img id="graph-image" alt="Loading graph..." />
    </div>
    
    <script>
        async function submitQA() {
            const question = document.getElementById('question').value;
            const answer = document.getElementById('answer').value;
            
            // Show loading state
            document.getElementById('questions-list').innerHTML = '<li>Processing...</li>';
            document.getElementById('graph-image').src = '';
            
            try {
                const response = await fetch('http://localhost:8058/investigation/submit-qa', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({question, answer})
                });
                
                const data = await response.json();
                
                // Display suggested questions
                const questionsList = document.getElementById('questions-list');
                questionsList.innerHTML = '';
                data.suggestedQuestions.forEach(q => {
                    const li = document.createElement('li');
                    li.textContent = q;
                    questionsList.appendChild(li);
                });
                
                // Display graph PNG
                document.getElementById('graph-image').src = data.graphUrl;
                
                // Clear form
                document.getElementById('question').value = '';
                document.getElementById('answer').value = '';
                
            } catch (error) {
                console.error('Error:', error);
                alert('Failed to submit Q&A. Check console for details.');
            }
        }
    </script>
</body>
</html>
```

### React Component

```jsx
import React, { useState } from 'react';

function InvestigationRoom() {
    const [question, setQuestion] = useState('');
    const [answer, setAnswer] = useState('');
    const [suggestedQuestions, setSuggestedQuestions] = useState([]);
    const [graphUrl, setGraphUrl] = useState('');
    const [loading, setLoading] = useState(false);
    
    const submitQA = async () => {
        setLoading(true);
        
        try {
            const response = await fetch('http://localhost:8058/investigation/submit-qa', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({question, answer})
            });
            
            const data = await response.json();
            
            setSuggestedQuestions(data.suggestedQuestions);
            setGraphUrl(data.graphUrl);
            setQuestion('');
            setAnswer('');
            
        } catch (error) {
            console.error('Error:', error);
            alert('Failed to submit Q&A');
        } finally {
            setLoading(false);
        }
    };
    
    return (
        <div className="investigation-room">
            <h1>Investigation Room</h1>
            
            <div className="qa-form">
                <input 
                    type="text" 
                    placeholder="Question"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                />
                <textarea 
                    placeholder="Answer"
                    value={answer}
                    onChange={(e) => setAnswer(e.target.value)}
                />
                <button onClick={submitQA} disabled={loading}>
                    {loading ? 'Processing...' : 'Submit'}
                </button>
            </div>
            
            <div className="suggested-questions">
                <h2>Suggested Questions:</h2>
                <ul>
                    {suggestedQuestions.map((q, i) => (
                        <li key={i}>{q}</li>
                    ))}
                </ul>
            </div>
            
            <div className="graph-visualization">
                <h2>Knowledge Graph:</h2>
                {graphUrl && <img src={graphUrl} alt="Knowledge Graph" />}
            </div>
        </div>
    );
}

export default InvestigationRoom;
```

---

## Troubleshooting

### Issue: "Failed to generate PNG"

**Solution:**
```bash
# Install required libraries
pip install networkx==3.2.1 matplotlib==3.8.2
```

### Issue: Graph regeneration takes too long

**Possible causes:**
- Large session.md file (many Q&As)
- Slow LLM API for entity extraction

**Solutions:**
- Use faster LLM model for ingestion (set `INGESTION_LLM_CHOICE`)
- Consider incremental graph updates instead of full regeneration
- Process graph generation in background (return immediately)

### Issue: Server crashes after Q&A submission

**Check logs for:**
- Neo4j connection errors
- File permission issues
- Memory issues with large graphs

---

## Clear Session and Start Fresh

To start a new investigation:

```bash
# Method 1: Delete the file manually
rm documents/session.md

# Method 2: Via API (if endpoint added)
curl -X DELETE "http://localhost:8058/investigation/clear-session"
```

Then the next Q&A will start a fresh `session.md` file.

---

## Differences from Previous Workflow

| Feature | Old (One-time ingestion) | New (Always-running server) |
|---------|--------------------------|------------------------------|
| **Execution** | `python -m ingestion.ingest --clean` | `python -m agent.api` (stays running) |
| **Storage** | Neo4j + PostgreSQL | session.md file + Neo4j |
| **Graph update** | Manual re-run | Automatic on each Q&A |
| **Output** | Graph data JSON | PNG image URL |
| **Usage** | Pre-process documents | Real-time Q&A capture |

---

## Summary

✅ **Server runs continuously**  
✅ **Q&A appended to session.md**  
✅ **Graph regenerated on each submission**  
✅ **PNG visualization generated**  
✅ **Suggested questions returned**  
✅ **Frontend receives PNG URL**  

The system is now ready for real-time investigation workflows! 🚀

