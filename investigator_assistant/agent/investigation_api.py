"""
Investigation-specific API endpoints for frontend integration.
"""

import os
import re
import logging
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from .models import (
    QASubmissionRequest,
    QASubmissionResponse,
    AnalysisChatRequest,
    AnalysisChatResponse,
    GraphVisualizationData,
    InvestigationAnalysis
)
from .agent import rag_agent, AgentDependencies
from .graph_utils import graph_client
from .graph_visualization import (
    get_graph_visualization_data,
    generate_graph_url
)
from .prompts import INVESTIGATION_QA_PROMPT
from .db_utils import create_session, add_message

logger = logging.getLogger(__name__)

# Create router for investigation endpoints
investigation_router = APIRouter(prefix="/investigation", tags=["investigation"])
analysis_router = APIRouter(prefix="/analysis", tags=["analysis"])
graph_router = APIRouter(prefix="/graph", tags=["graph"])


def extract_questions_from_text(text: str, max_questions: int = 5) -> List[str]:
    """
    Extract questions from agent response text.
    
    Supports multiple formats:
    - Numbered lists: "1. Question?"
    - Bulleted lists: "- Question?" or "• Question?"
    - Standalone questions on separate lines
    
    Args:
        text: Agent response text
        max_questions: Maximum number of questions to extract
    
    Returns:
        List of extracted questions
    """
    questions = []
    
    # Pattern 1: Numbered lists (1. Question? or 1) Question?)
    numbered_pattern = r'^\s*\d+[\.\)]\s+(.+\?)\s*$'
    
    # Pattern 2: Bulleted lists (- Question? or • Question? or * Question?)
    bulleted_pattern = r'^\s*[-•*]\s+(.+\?)\s*$'
    
    # Pattern 3: Standalone questions (line starts with capital, ends with ?)
    standalone_pattern = r'^\s*([A-Z].+\?)\s*$'
    
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Try numbered pattern
        match = re.match(numbered_pattern, line, re.MULTILINE)
        if match:
            questions.append(match.group(1).strip())
            continue
        
        # Try bulleted pattern
        match = re.match(bulleted_pattern, line, re.MULTILINE)
        if match:
            questions.append(match.group(1).strip())
            continue
        
        # Try standalone pattern (but only in sections that look like questions)
        if '?' in line and len(line) > 20:  # Avoid short fragments
            match = re.match(standalone_pattern, line)
            if match:
                questions.append(match.group(1).strip())
    
    # Remove duplicates while preserving order
    seen = set()
    unique_questions = []
    for q in questions:
        q_normalized = q.lower().strip()
        if q_normalized not in seen:
            seen.add(q_normalized)
            unique_questions.append(q)
    
    return unique_questions[:max_questions]


async def analyze_qa_pair(
    question: str,
    answer: str,
    session_id: Optional[str] = None
) -> InvestigationAnalysis:
    """
    Analyze a Q&A pair using the agent.
    
    Args:
        question: The question asked
        answer: The suspect's answer
        session_id: Optional session ID for context
    
    Returns:
        InvestigationAnalysis with structured output
    """
    try:
        # Create or use existing session
        if not session_id:
            session_id = await create_session(
                user_id="investigation_system",
                metadata={"type": "qa_analysis"}
            )
        
        # Build analysis prompt
        prompt = INVESTIGATION_QA_PROMPT.format(
            question=question,
            answer=answer
        )
        
        # Create dependencies
        deps = AgentDependencies(session_id=session_id)
        
        # Try to get structured output first
        try:
            result = await rag_agent.run(
                prompt,
                deps=deps,
                result_type=InvestigationAnalysis
            )
            return result.data
        except Exception as e:
            logger.warning(f"Structured output failed, falling back to text parsing: {e}")
            
            # Fallback: run without structured output and parse manually
            result = await rag_agent.run(prompt, deps=deps)
            response_text = result.data
            
            # Extract questions from text
            questions = extract_questions_from_text(response_text)
            
            # Split analysis and questions sections
            analysis_text = response_text
            if "**Suggested Questions:**" in response_text:
                parts = response_text.split("**Suggested Questions:**")
                analysis_text = parts[0].replace("**Analysis:**", "").strip()
            elif "Suggested Questions:" in response_text:
                parts = response_text.split("Suggested Questions:")
                analysis_text = parts[0].replace("Analysis:", "").strip()
            
            # Create structured response manually
            return InvestigationAnalysis(
                analysis=analysis_text,
                suggested_questions=questions if questions else [
                    "What additional details can you provide about this situation?",
                    "Can you clarify the timeline of events?",
                    "Who else was involved or present?"
                ],
                contradictions_found=[],
                missing_information=[],
                key_entities=[]
            )
    
    except Exception as e:
        logger.error(f"Failed to analyze Q&A pair: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@investigation_router.post("/submit-qa", response_model=QASubmissionResponse)
async def submit_qa(request: QASubmissionRequest):
    """
    Submit a Q&A pair from the Investigation Room.
    
    This endpoint:
    1. Adds the Q&A to the knowledge graph as an episode
    2. Analyzes the answer for gaps, contradictions, and ambiguities
    3. Generates suggested follow-up questions
    4. Returns the graph visualization URL
    """
    try:
        logger.info(f"Received Q&A submission: Q='{request.question[:50]}...' A='{request.answer[:50]}...'")
        
        # Get or create session
        session_id = request.session_id
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Step 1: Add Q&A to knowledge graph
        if graph_client and graph_client._initialized:
            try:
                # Combine Q&A into episode content
                episode_content = f"Q: {request.question}\nA: {request.answer}"
                
                await graph_client.add_episode(
                    episode_id=str(uuid.uuid4()),
                    content=episode_content,
                    source="investigation_room",
                    timestamp=datetime.now(timezone.utc),
                    metadata={
                        "question": request.question,
                        "answer": request.answer,
                        "session_id": session_id
                    }
                )
                logger.info("Successfully added Q&A to knowledge graph")
            except Exception as e:
                logger.error(f"Failed to add Q&A to knowledge graph: {e}")
                # Continue anyway - we can still analyze
        else:
            logger.warning("Graph client not initialized, skipping graph update")
        
        # Step 1b: Also save Q&A to PostgreSQL messages table for backup/querying
        try:
            # Save the question as a "user" message
            await add_message(
                session_id=session_id,
                role="user",
                content=request.question,
                metadata={
                    "source": "investigation_room",
                    "type": "interrogation_question"
                }
            )
            
            # Save the answer as an "assistant" message (or could use "user" for suspect's answer)
            await add_message(
                session_id=session_id,
                role="assistant",  # Using "assistant" to represent the suspect's response
                content=request.answer,
                metadata={
                    "source": "investigation_room",
                    "type": "suspect_answer"
                }
            )
            logger.info("Successfully saved Q&A to PostgreSQL")
        except Exception as e:
            logger.error(f"Failed to save Q&A to PostgreSQL: {e}")
            # Continue anyway - graph storage is primary
        
        # Step 2: Analyze the Q&A pair
        analysis = await analyze_qa_pair(
            question=request.question,
            answer=request.answer,
            session_id=session_id
        )
        
        logger.info(f"Analysis complete, found {len(analysis.suggested_questions)} questions")
        
        # Step 3: Generate graph URL
        graph_url = generate_graph_url(session_id=session_id)
        
        # Step 4: Return response
        return QASubmissionResponse(
            suggestedQuestions=analysis.suggested_questions,
            graphUrl=graph_url,
            analysis=analysis.analysis,
            session_id=session_id
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Q&A submission failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process Q&A submission: {str(e)}"
        )


@analysis_router.post("/chat", response_model=AnalysisChatResponse)
async def analysis_chat(request: AnalysisChatRequest):
    """
    Handle chat prompts from the Knowledge Graph & Analysis interface.
    
    This is a stateless endpoint - no conversation history is maintained.
    Each prompt is treated independently.
    """
    try:
        logger.info(f"Received analysis chat prompt: '{request.prompt[:100]}...'")
        
        # Create temporary session for this request
        temp_session_id = f"temp_{uuid.uuid4()}"
        
        # Create dependencies
        deps = AgentDependencies(session_id=temp_session_id)
        
        # Run agent with the prompt
        result = await rag_agent.run(request.prompt, deps=deps)
        response_text = result.data
        
        logger.info(f"Analysis chat complete, response length: {len(response_text)}")
        
        return AnalysisChatResponse(answer=response_text)
    
    except Exception as e:
        logger.error(f"Analysis chat failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process analysis chat: {str(e)}"
        )


@graph_router.get("/data", response_model=GraphVisualizationData)
async def get_graph_data(
    session_id: Optional[str] = None,
    limit: int = 50
):
    """
    Get graph visualization data for frontend rendering.
    
    Returns nodes and edges in a format suitable for D3.js, vis.js, or similar libraries.
    
    Args:
        session_id: Optional session ID to filter by
        limit: Maximum number of nodes to return (default: 50)
    """
    try:
        logger.info(f"Fetching graph data (limit={limit}, session={session_id})")
        
        graph_data = await get_graph_visualization_data(
            limit=limit,
            session_id=session_id
        )
        
        logger.info(f"Retrieved {len(graph_data.nodes)} nodes and {len(graph_data.edges)} edges")
        
        return graph_data
    
    except Exception as e:
        logger.error(f"Failed to get graph data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve graph data: {str(e)}"
        )


# Export routers for inclusion in main app
__all__ = [
    "investigation_router",
    "analysis_router",
    "graph_router",
    "extract_questions_from_text",
    "analyze_qa_pair"
]

