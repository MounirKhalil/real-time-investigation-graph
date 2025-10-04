"""
File-based storage for investigation sessions.
Appends Q&A to markdown file and regenerates graph.
"""

import os
import logging
import asyncio
from pathlib import Path
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Path to the session file
SESSION_FILE = Path(__file__).parent.parent / "documents" / "session.md"


async def append_qa_to_file(question: str, answer: str) -> bool:
    """
    Append Q&A to the session.md file.
    
    Args:
        question: The investigator's question
        answer: The suspect's answer
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Format the Q&A
        qa_text = f"\nInvestigator: {question}\nSuspect: {answer}\n"
        
        # Ensure the documents directory exists
        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Append to file
        with open(SESSION_FILE, 'a', encoding='utf-8') as f:
            f.write(qa_text)
        
        logger.info(f"Successfully appended Q&A to {SESSION_FILE}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to append Q&A to file: {e}")
        return False


def get_session_content() -> str:
    """
    Read the current content of session.md
    
    Returns:
        File content as string
    """
    try:
        if SESSION_FILE.exists():
            with open(SESSION_FILE, 'r', encoding='utf-8') as f:
                return f.read()
        return ""
    except Exception as e:
        logger.error(f"Failed to read session file: {e}")
        return ""


async def regenerate_graph() -> bool:
    """
    Re-run ingestion on the session.md file to regenerate the graph.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        from ..ingestion.ingest import DocumentIngestionPipeline
        from ..agent.models import IngestionConfig
        
        logger.info("Starting graph regeneration...")
        
        # Create ingestion config
        config = IngestionConfig(
            chunk_size=1000,
            chunk_overlap=200,
            use_semantic_chunking=True,
            extract_entities=True,
            skip_graph_building=False
        )
        
        # Create pipeline
        pipeline = DocumentIngestionPipeline(
            config=config,
            documents_folder=str(SESSION_FILE.parent),
            clean_before_ingest=True  # Clean and re-ingest
        )
        
        # Initialize
        await pipeline.initialize()
        
        # Ingest the session file
        results = await pipeline.ingest_documents()
        
        # Close
        await pipeline.close()
        
        logger.info(f"Graph regeneration complete: {len(results)} documents processed")
        return True
        
    except Exception as e:
        logger.error(f"Failed to regenerate graph: {e}")
        return False


async def generate_graph_png() -> Optional[str]:
    """
    Generate a PNG image of the current knowledge graph.
    
    Returns:
        Path to the generated PNG file, or None if failed
    """
    try:
        from ..agent.graph_utils import graph_client
        import subprocess
        
        if not graph_client or not graph_client._initialized:
            logger.error("Graph client not initialized")
            return None
        
        # Create static directory for images
        static_dir = Path(__file__).parent.parent / "static" / "graphs"
        static_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        png_file = static_dir / f"graph_{timestamp}.png"
        
        # Export graph data from Neo4j
        cypher_query = """
        MATCH (n:Entity)-[r:RELATES_TO]-(m:Entity)
        RETURN n.name as source, type(r) as relationship, m.name as target
        LIMIT 100
        """
        
        # Use Neo4j's visualization tools or Python graphviz
        # For now, we'll use a simple approach with networkx + matplotlib
        try:
            import networkx as nx
            import matplotlib
            matplotlib.use('Agg')  # Use non-interactive backend
            import matplotlib.pyplot as plt
            
            # Create graph
            G = nx.Graph()
            
            # Query Neo4j for data
            async with graph_client.graphiti.driver.session() as session:
                result = await session.run(cypher_query)
                edges = []
                async for record in result:
                    source = record.get("source", "Unknown")
                    target = record.get("target", "Unknown")
                    relationship = record.get("relationship", "relates_to")
                    if source and target:
                        edges.append((source, target, relationship))
                        G.add_edge(source, target, label=relationship)
            
            if G.number_of_nodes() == 0:
                logger.warning("No nodes in graph to visualize")
                return None
            
            # Create visualization
            plt.figure(figsize=(16, 12))
            pos = nx.spring_layout(G, k=2, iterations=50)
            
            # Draw nodes
            nx.draw_networkx_nodes(G, pos, node_color='lightblue', 
                                   node_size=3000, alpha=0.9)
            
            # Draw edges
            nx.draw_networkx_edges(G, pos, width=2, alpha=0.6, edge_color='gray')
            
            # Draw labels
            nx.draw_networkx_labels(G, pos, font_size=10, font_weight='bold')
            
            # Draw edge labels
            edge_labels = nx.get_edge_attributes(G, 'label')
            nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=8)
            
            plt.axis('off')
            plt.tight_layout()
            plt.savefig(png_file, format='png', dpi=150, bbox_inches='tight')
            plt.close()
            
            logger.info(f"Generated graph PNG: {png_file}")
            return str(png_file.relative_to(Path(__file__).parent.parent))
            
        except ImportError as ie:
            logger.error(f"Missing required libraries for graph visualization: {ie}")
            logger.info("Install with: pip install networkx matplotlib")
            return None
            
    except Exception as e:
        logger.error(f"Failed to generate graph PNG: {e}")
        return None


async def clear_session_file() -> bool:
    """
    Clear the session.md file (start fresh).
    
    Returns:
        True if successful
    """
    try:
        with open(SESSION_FILE, 'w', encoding='utf-8') as f:
            f.write("")
        logger.info("Session file cleared")
        return True
    except Exception as e:
        logger.error(f"Failed to clear session file: {e}")
        return False

