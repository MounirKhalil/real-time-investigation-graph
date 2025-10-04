# Quick Start - File-Based Investigation Workflow

## 🚀 Get Started in 3 Steps

### Step 1: Install New Dependencies

```bash
pip install networkx==3.2.1 matplotlib==3.8.2
```

### Step 2: Start the Always-Running Server

```bash
python -m agent.api
```

**✅ Server is now running on http://localhost:8058**

### Step 3: Test with a Q&A Submission

Open a new terminal and run:

```bash
curl -X POST "http://localhost:8058/investigation/submit-qa" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Michael, where were you on the evening of June 12th around 8 p.m.?",
    "answer": "I was at Jack'\''s Diner on 5th Street."
  }'
```

---

## What Happens?

1. **Q&A is appended** to `documents/session.md`:
   ```markdown
   Investigator: Please state your name for the record.
   Suspect: My name is Michael Turner.
   
   Investigator: Michael, where were you on the evening of June 12th around 8 p.m.?
   Suspect: I was at Jack's Diner on 5th Street.
   ```

2. **Knowledge graph is regenerated** from the entire file (5-15 seconds)

3. **PNG visualization is created** in `static/graphs/graph_TIMESTAMP.png`

4. **Suggested questions are generated** by AI agent

5. **Response is returned** with PNG URL:
   ```json
   {
     "suggestedQuestions": [
       "What time did you arrive at Jack's Diner?",
       "Who were you with at Jack's Diner?",
       "How long did you stay?",
       "What did you order?",
       "Can anyone confirm you were there?"
     ],
     "graphUrl": "http://localhost:8058/static/graphs/graph_20250115_103045.png"
   }
   ```

---

## View the Graph

Open the PNG URL in your browser:
```
http://localhost:8058/static/graphs/graph_20250115_103045.png
```

Or embed in HTML:
```html
<img src="http://localhost:8058/static/graphs/graph_20250115_103045.png" />
```

---

## Current session.md Content

Check what's currently in the file:

```bash
cat documents/session.md
```

---

## Start Fresh Investigation

To clear the session and start over:

```bash
# Delete the file
rm documents/session.md

# Or create a new empty one
echo "" > documents/session.md
```

---

## Frontend Integration

```javascript
async function submitQA(question, answer) {
    const response = await fetch('http://localhost:8058/investigation/submit-qa', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({question, answer})
    });
    
    const data = await response.json();
    
    // Display suggested questions
    data.suggestedQuestions.forEach(q => console.log(q));
    
    // Display graph PNG
    document.getElementById('graph').src = data.graphUrl;
}
```

---

## Key Differences from Before

| Before | Now |
|--------|-----|
| Run ingestion once | Server always running |
| Manual re-run needed | Auto-updates on each Q&A |
| Graph data JSON | Graph PNG image |
| Pre-process documents | Real-time Q&A capture |

---

## Processing Time

Expect **8-25 seconds** per Q&A:
- Append to file: <10ms
- Regenerate graph: 5-15s
- Generate PNG: 1-2s
- Analyze Q&A: 2-8s

---

## Need Help?

- Full documentation: `FILE_BASED_WORKFLOW.md`
- Storage details: `DATA_STORAGE.md`
- API testing: `TESTING_GUIDE.md`

---

**That's it! Your investigation system is ready! 🎉**

