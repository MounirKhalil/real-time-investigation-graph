#!/usr/bin/env python3
"""
Quick test script for frontend integration endpoints.

Usage:
    python test_endpoints.py
"""

import requests
import json
from typing import Dict, Any


BASE_URL = "http://localhost:8058"


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_json(data: Dict[str, Any]):
    """Pretty print JSON data."""
    print(json.dumps(data, indent=2))


def test_health():
    """Test health endpoint."""
    print_section("Testing Health Endpoint")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        response.raise_for_status()
        
        data = response.json()
        print(f"Status: {data['status']}")
        print(f"Database: {'✓' if data['database'] else '✗'}")
        print(f"Graph Database: {'✓' if data['graph_database'] else '✗'}")
        print(f"LLM Connection: {'✓' if data['llm_connection'] else '✗'}")
        
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


def test_qa_submission():
    """Test Q&A submission endpoint."""
    print_section("Testing Q&A Submission")
    
    payload = {
        "question": "Where were you last Friday evening?",
        "answer": "I was at a restaurant downtown with my friend Mike. We had dinner and talked about business."
    }
    
    print("Sending Q&A:")
    print(f"  Q: {payload['question']}")
    print(f"  A: {payload['answer']}")
    print()
    
    try:
        response = requests.post(
            f"{BASE_URL}/investigation/submit-qa",
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        
        print("✓ Q&A Submitted Successfully")
        print(f"\nSession ID: {data.get('session_id')}")
        print(f"\nSuggested Questions ({len(data['suggestedQuestions'])}):")
        for i, question in enumerate(data['suggestedQuestions'], 1):
            print(f"  {i}. {question}")
        
        print(f"\nGraph URL: {data['graphUrl']}")
        
        if data.get('analysis'):
            print(f"\nAnalysis:")
            print(f"  {data['analysis'][:200]}...")
        
        return data.get('session_id')
    
    except requests.exceptions.Timeout:
        print("❌ Request timed out (this is normal for first request - try again)")
        return None
    except Exception as e:
        print(f"❌ Q&A submission failed: {e}")
        return None


def test_analysis_chat():
    """Test analysis chat endpoint."""
    print_section("Testing Analysis Chat")
    
    payload = {
        "prompt": "What information do we have about Mike from the interrogation?"
    }
    
    print(f"Sending prompt: {payload['prompt']}")
    print()
    
    try:
        response = requests.post(
            f"{BASE_URL}/analysis/chat",
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        
        print("✓ Chat Response Received")
        print(f"\nAssistant's Answer:")
        print(f"  {data['answer']}")
        
        return True
    
    except requests.exceptions.Timeout:
        print("❌ Request timed out (this is normal for first request - try again)")
        return False
    except Exception as e:
        print(f"❌ Analysis chat failed: {e}")
        return False


def test_graph_data(session_id: str = None):
    """Test graph data endpoint."""
    print_section("Testing Graph Data Endpoint")
    
    url = f"{BASE_URL}/graph/data?limit=20"
    if session_id:
        url += f"&session_id={session_id}"
    
    print(f"Fetching graph data (limit=20)...")
    print()
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        print("✓ Graph Data Retrieved")
        print(f"\nNodes: {len(data['nodes'])}")
        print(f"Edges: {len(data['edges'])}")
        
        if data['nodes']:
            print(f"\nSample Node:")
            node = data['nodes'][0]
            print(f"  ID: {node['id']}")
            print(f"  Label: {node['label']}")
            print(f"  Type: {node['type']}")
        
        if data['edges']:
            print(f"\nSample Edge:")
            edge = data['edges'][0]
            print(f"  From: {edge['from']}")
            print(f"  To: {edge['to']}")
            print(f"  Label: {edge['label']}")
        
        return True
    
    except Exception as e:
        print(f"❌ Graph data retrieval failed: {e}")
        return False


def test_contradiction_detection():
    """Test contradiction detection by submitting conflicting statements."""
    print_section("Testing Contradiction Detection")
    
    print("Submitting first statement...")
    payload1 = {
        "question": "What time did you meet Mike?",
        "answer": "I met Mike around 6 PM on Friday."
    }
    
    try:
        response1 = requests.post(
            f"{BASE_URL}/investigation/submit-qa",
            json=payload1,
            timeout=30
        )
        response1.raise_for_status()
        print("✓ First statement submitted")
        
        print("\nSubmitting contradictory statement...")
        payload2 = {
            "question": "Can you confirm the meeting time with Mike?",
            "answer": "Actually, it was Saturday at 8 PM."
        }
        
        response2 = requests.post(
            f"{BASE_URL}/investigation/submit-qa",
            json=payload2,
            timeout=30
        )
        response2.raise_for_status()
        data = response2.json()
        
        print("✓ Second statement submitted")
        print("\nSuggested Questions (should detect contradiction):")
        for i, question in enumerate(data['suggestedQuestions'], 1):
            print(f"  {i}. {question}")
        
        # Check if any question mentions contradiction or discrepancy
        questions_text = ' '.join(data['suggestedQuestions']).lower()
        if 'contradict' in questions_text or 'discrepancy' in questions_text or 'friday' in questions_text or 'saturday' in questions_text:
            print("\n✓ Contradiction potentially detected in questions!")
        
        return True
    
    except Exception as e:
        print(f"❌ Contradiction test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("  FRONTEND INTEGRATION ENDPOINT TESTS")
    print("=" * 70)
    print(f"\nBase URL: {BASE_URL}")
    print("\nNote: First requests may take longer due to initialization")
    
    # Test 1: Health check
    if not test_health():
        print("\n⚠️  Server not healthy. Check if API is running on port 8058")
        print("   Start with: python -m agent.api")
        return
    
    # Test 2: Q&A submission
    session_id = test_qa_submission()
    
    # Test 3: Graph data
    test_graph_data(session_id)
    
    # Test 4: Analysis chat
    test_analysis_chat()
    
    # Test 5: Contradiction detection
    test_contradiction_detection()
    
    # Summary
    print_section("Test Summary")
    print("✓ All endpoint tests completed")
    print("\nNext steps:")
    print("  1. Integrate these endpoints with your frontend")
    print("  2. Implement graph visualization rendering")
    print("  3. Add error handling and loading states")
    print("\nFor more details, see FRONTEND_INTEGRATION.md and TESTING_GUIDE.md")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        raise

