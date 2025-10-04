# Q&A Data Storage Architecture

## Overview

Q&A pairs submitted from the Investigation Room are stored in **TWO locations** for redundancy, querying flexibility, and different use cases.

---

## Storage Locations

### 1. **Neo4j Knowledge Graph** (Primary - via Graphiti)

**Purpose:** Semantic understanding, entity relationships, contradiction detection

**What's stored:**
- Full Q&A episodes as graph nodes
- Extracted entities (people, places, times, events)
- Relationships between entities
- Temporal validity of facts
- Episode metadata (session_id, timestamps, source)

**Storage format:**
```
Episode Node:
  - id: UUID
  - content: "Q: {question}\nA: {answer}"
  - source: "investigation_room"
  - timestamp: ISO datetime
  - metadata: {question, answer, session_id}

Entity Nodes (auto-extracted):
  - name: "Mike Johnson"
  - type: "Person"
  - created_at: timestamp
  - summary: "Friend mentioned in restaurant meeting"

Relationships (auto-created):
  - from: Suspect entity
  - to: Mike entity
  - type: "met_with"
  - fact: "Suspect met with Mike at restaurant"
```

**Advantages:**
- ✅ Automatic entity extraction
- ✅ Relationship discovery
- ✅ Temporal tracking
- ✅ Graph traversal for finding connections
- ✅ Contradiction detection across statements

**Disadvantages:**
- ❌ Slower processing (entity extraction takes 5-10 seconds)
- ❌ More complex queries (Cypher required)
- ❌ Not ideal for simple chronological retrieval

---

### 2. **PostgreSQL Messages Table** (Backup/Query)

**Purpose:** Backup, chronological querying, session tracking

**What's stored:**
- Question as "user" role message
- Answer as "assistant" role message
- Session association
- Timestamps
- Metadata tags

**Schema:**
```sql
-- From sql/schema.sql
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

**Storage format:**
```sql
-- Question (user message)
INSERT INTO messages (session_id, role, content, metadata)
VALUES (
  'abc-123-def-456',
  'user',
  'Where were you Friday night?',
  '{"source": "investigation_room", "type": "interrogation_question"}'
);

-- Answer (assistant message)
INSERT INTO messages (session_id, role, content, metadata)
VALUES (
  'abc-123-def-456',
  'assistant',
  'I was at a restaurant with Mike.',
  '{"source": "investigation_room", "type": "suspect_answer"}'
);
```

**Advantages:**
- ✅ Fast storage (<100ms)
- ✅ Easy chronological queries (ORDER BY created_at)
- ✅ Simple SQL queries
- ✅ Backup if Neo4j fails
- ✅ Links to sessions table

**Disadvantages:**
- ❌ No entity extraction
- ❌ No relationship discovery
- ❌ No semantic understanding

---

## Code Implementation

### Where Storage Happens

In `investigator_assistant/agent/investigation_api.py`:

```python
@investigation_router.post("/submit-qa")
async def submit_qa(request: QASubmissionRequest):
    # Storage Step 1: Neo4j Knowledge Graph
    await graph_client.add_episode(
        episode_id=str(uuid.uuid4()),
        content=f"Q: {request.question}\nA: {request.answer}",
        source="investigation_room",
        timestamp=datetime.now(timezone.utc),
        metadata={
            "question": request.question,
            "answer": request.answer,
            "session_id": session_id
        }
    )
    
    # Storage Step 2: PostgreSQL Messages
    await add_message(
        session_id=session_id,
        role="user",
        content=request.question,
        metadata={
            "source": "investigation_room",
            "type": "interrogation_question"
        }
    )
    
    await add_message(
        session_id=session_id,
        role="assistant",
        content=request.answer,
        metadata={
            "source": "investigation_room",
            "type": "suspect_answer"
        }
    )
```

---

## Querying Stored Q&As

### From PostgreSQL (Simple Chronological View)

```sql
-- Get all Q&A pairs for a session
SELECT 
    role,
    content,
    created_at,
    metadata->>'type' as message_type
FROM messages
WHERE session_id = 'abc-123-def-456'
  AND metadata->>'source' = 'investigation_room'
ORDER BY created_at;

-- Result:
-- role      | content                          | created_at           | message_type
-- ----------|----------------------------------|----------------------|----------------------
-- user      | Where were you Friday night?     | 2025-01-15 10:30:00 | interrogation_question
-- assistant | I was at a restaurant with Mike. | 2025-01-15 10:30:05 | suspect_answer
```

### From Neo4j (Entity and Relationship View)

```cypher
// Get all episodes from investigation room
MATCH (e:Episode {source: 'investigation_room'})
RETURN e.content, e.timestamp
ORDER BY e.timestamp;

// Get entities mentioned in Q&A
MATCH (e:Episode)-[:MENTIONS]->(entity:Entity)
WHERE e.source = 'investigation_room'
RETURN entity.name, entity.type, count(e) as mentions
ORDER BY mentions DESC;

// Find relationships between entities
MATCH (e1:Entity)-[r:RELATES_TO]-(e2:Entity)
RETURN e1.name, type(r), e2.name, r.fact;
```

### Via API Endpoints

```bash
# Get messages for a session from PostgreSQL
curl "http://localhost:8058/sessions/{session_id}"

# Get graph data from Neo4j
curl "http://localhost:8058/graph/data?session_id={session_id}"

# Query via analysis chat (searches both)
curl -X POST "http://localhost:8058/analysis/chat" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Show me all Q&A about Friday night"}'
```

---

## Data Flow

```
Frontend: Submit Q&A
    ↓
POST /investigation/submit-qa
    ↓
Backend:
  ┌─────────────────────────────────┐
  │ 1. Save to Neo4j (Graphiti)     │
  │    - Create episode             │
  │    - Extract entities           │ → 5-10 seconds
  │    - Build relationships        │
  └─────────────────────────────────┘
  ┌─────────────────────────────────┐
  │ 2. Save to PostgreSQL           │
  │    - Save question (user)       │ → <100ms
  │    - Save answer (assistant)    │
  └─────────────────────────────────┘
  ┌─────────────────────────────────┐
  │ 3. Run agent analysis           │
  │    - Search for contradictions  │ → 2-8 seconds
  │    - Generate questions         │
  └─────────────────────────────────┘
    ↓
Response: {suggestedQuestions, graphUrl}
```

---

## Session Management

Both storage systems link to the same session:

```sql
-- Sessions table (PostgreSQL)
CREATE TABLE sessions (
    id UUID PRIMARY KEY,
    user_id TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE
);
```

**Session metadata includes:**
- `type`: "qa_analysis" or "investigation"
- `user_id`: Investigator ID
- Custom fields as needed

---

## Retrieval Examples

### Get Complete Investigation History

**Method 1: PostgreSQL (Chronological)**
```python
import asyncpg

async def get_investigation_history(session_id: str):
    async with db_pool.acquire() as conn:
        messages = await conn.fetch("""
            SELECT role, content, created_at, metadata
            FROM messages
            WHERE session_id = $1
              AND metadata->>'source' = 'investigation_room'
            ORDER BY created_at
        """, session_id)
    return messages
```

**Method 2: Neo4j (Entity-focused)**
```python
from investigator_assistant.agent.graph_visualization import get_graph_visualization_data

async def get_investigation_graph(session_id: str):
    graph_data = await get_graph_visualization_data(
        session_id=session_id,
        limit=100
    )
    return graph_data  # {nodes: [], edges: []}
```

**Method 3: Hybrid (Best of both)**
```python
async def get_complete_investigation(session_id: str):
    # Get chronological Q&A from PostgreSQL
    messages = await get_investigation_history(session_id)
    
    # Get entity graph from Neo4j
    graph = await get_investigation_graph(session_id)
    
    return {
        "timeline": messages,
        "knowledge_graph": graph
    }
```

---

## Consistency & Error Handling

### What happens if storage fails?

**Neo4j fails:**
- ✅ PostgreSQL still saves Q&A
- ✅ Analysis continues
- ⚠️ No entity extraction
- ⚠️ No relationship detection

**PostgreSQL fails:**
- ✅ Neo4j still saves episode
- ✅ Analysis continues
- ⚠️ No backup in relational DB

**Both fail:**
- ❌ Q&A not persisted
- ✅ Analysis still runs (uses in-memory data)
- ⚠️ User sees error but gets suggested questions

### Implemented safeguards:

```python
# Each storage operation is wrapped in try-catch
try:
    await graph_client.add_episode(...)
    logger.info("Successfully added Q&A to knowledge graph")
except Exception as e:
    logger.error(f"Failed to add Q&A to knowledge graph: {e}")
    # Continue anyway - we can still analyze

try:
    await add_message(...)
    logger.info("Successfully saved Q&A to PostgreSQL")
except Exception as e:
    logger.error(f"Failed to save Q&A to PostgreSQL: {e}")
    # Continue anyway - graph storage is primary
```

---

## Performance Impact

### Storage Times:

| Operation | Time | Notes |
|-----------|------|-------|
| PostgreSQL insert | <100ms | Very fast |
| Neo4j episode creation | 1-2s | Creating nodes |
| Entity extraction (Graphiti) | 5-10s | LLM processing |
| Total storage time | 5-12s | Most time in entity extraction |

### Optimization Options:

1. **Async entity extraction** - Return response immediately, extract entities in background
2. **Batch processing** - Extract entities from multiple Q&As at once
3. **Caching** - Cache entity extraction results for similar answers
4. **Selective extraction** - Only extract entities for important Q&As

---

## Data Privacy & Security

### Current Implementation:
- ❌ No encryption at rest
- ❌ No field-level encryption
- ✅ Session isolation (Q&As linked by session_id)
- ✅ Soft delete via session deletion (CASCADE)

### Recommendations:
- Encrypt sensitive fields in PostgreSQL
- Use Neo4j encryption features
- Implement access control by session owner
- Add audit logging for Q&A access

---

## Backup & Recovery

### PostgreSQL Backup:
```bash
# Backup messages table
pg_dump -t messages -t sessions -d $DATABASE_URL > qa_backup.sql

# Restore
psql -d $DATABASE_URL < qa_backup.sql
```

### Neo4j Backup:
```bash
# Export all investigation episodes
cypher-shell "MATCH (e:Episode {source: 'investigation_room'})
              RETURN e" > episodes_backup.json

# Or use Neo4j backup tools
neo4j-admin backup --to=/backups/investigation
```

---

## Summary

### Dual Storage Benefits:
✅ **Redundancy** - Data preserved even if one system fails  
✅ **Performance** - PostgreSQL for fast queries, Neo4j for semantic analysis  
✅ **Flexibility** - Choose best tool for each query type  
✅ **Compliance** - Relational DB for audit trails, graph for analysis  

### Storage Decision Matrix:

| Use Case | Use PostgreSQL | Use Neo4j |
|----------|----------------|-----------|
| Get chronological Q&A list | ✅ | ❌ |
| Find entity relationships | ❌ | ✅ |
| Detect contradictions | ❌ | ✅ |
| Export Q&A for review | ✅ | ❌ |
| Backup/archive | ✅ | ❌ |
| Graph visualization | ❌ | ✅ |
| Session management | ✅ | ❌ |
| Timeline analysis | ✅ | ❌ |
| Semantic search | 50/50 | ✅ |

---

## Future Enhancements

1. **Add transaction coordinator** - Ensure both storages succeed or both fail
2. **Implement event sourcing** - Store Q&A as events for replay
3. **Add change data capture** - Sync between databases automatically
4. **Implement sharding** - Distribute Q&As across multiple nodes
5. **Add real-time sync** - Push updates to connected clients via WebSocket

