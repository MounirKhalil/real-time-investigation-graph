"""
Graph visualization utilities for extracting and formatting knowledge graph data.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .models import GraphNode, GraphEdge, GraphVisualizationData
from .graph_utils import graph_client

logger = logging.getLogger(__name__)


async def get_graph_visualization_data(
    limit: int = 50,
    session_id: Optional[str] = None
) -> GraphVisualizationData:
    """
    Extract graph data from Neo4j for frontend visualization.
    
    Args:
        limit: Maximum number of nodes to return
        session_id: Optional session ID to filter by
    
    Returns:
        GraphVisualizationData with nodes and edges
    """
    if not graph_client or not graph_client._initialized:
        logger.warning("Graph client not initialized, returning empty graph")
        return GraphVisualizationData(
            nodes=[],
            edges=[],
            metadata={"error": "Graph not available"}
        )
    
    try:
        # Get graph data from Neo4j using Graphiti
        nodes_data = []
        edges_data = []
        
        # Query for entity nodes
        entity_query = """
        MATCH (n:Entity)
        RETURN n.uuid as id, n.name as label, n.entity_type as type, 
               n.created_at as created_at, n.summary as summary
        ORDER BY n.created_at DESC
        LIMIT $limit
        """
        
        async with graph_client.graphiti.driver.session() as session:
            # Get entities
            result = await session.run(entity_query, limit=limit)
            async for record in result:
                node_id = record["id"]
                label = record["label"] or "Unknown"
                node_type = record["type"] or "Entity"
                created_at = record.get("created_at")
                summary = record.get("summary")
                
                nodes_data.append(GraphNode(
                    id=node_id,
                    label=label,
                    type=node_type,
                    metadata={
                        "created_at": created_at.isoformat() if created_at else None,
                        "summary": summary
                    }
                ))
        
        # Get node IDs for querying relationships
        if nodes_data:
            node_ids = [node.id for node in nodes_data]
            
            # Query for relationships between these entities
            edge_query = """
            MATCH (source:Entity)-[r:RELATES_TO]->(target:Entity)
            WHERE source.uuid IN $node_ids AND target.uuid IN $node_ids
            RETURN source.uuid as from_id, target.uuid as to_id, 
                   r.relationship_type as label, r.fact as fact,
                   r.created_at as created_at
            """
            
            async with graph_client.graphiti.driver.session() as session:
                result = await session.run(edge_query, node_ids=node_ids)
                async for record in result:
                    from_id = record["from_id"]
                    to_id = record["to_id"]
                    label = record.get("label") or "relates_to"
                    fact = record.get("fact")
                    created_at = record.get("created_at")
                    
                    edges_data.append(GraphEdge(
                        from_node=from_id,
                        to_node=to_id,
                        label=label,
                        metadata={
                            "fact": fact,
                            "created_at": created_at.isoformat() if created_at else None
                        }
                    ))
        
        metadata = {
            "total_nodes": len(nodes_data),
            "total_edges": len(edges_data),
            "limit": limit,
            "timestamp": datetime.now().isoformat()
        }
        
        return GraphVisualizationData(
            nodes=nodes_data,
            edges=edges_data,
            metadata=metadata
        )
        
    except Exception as e:
        logger.error(f"Failed to extract graph visualization data: {e}")
        return GraphVisualizationData(
            nodes=[],
            edges=[],
            metadata={"error": str(e)}
        )


async def get_recent_graph_changes(
    since_timestamp: Optional[datetime] = None,
    limit: int = 20
) -> GraphVisualizationData:
    """
    Get recently added or modified nodes and edges.
    
    Args:
        since_timestamp: Only include changes after this timestamp
        limit: Maximum number of nodes to return
    
    Returns:
        GraphVisualizationData with recent changes
    """
    if not graph_client or not graph_client._initialized:
        logger.warning("Graph client not initialized")
        return GraphVisualizationData(nodes=[], edges=[])
    
    try:
        nodes_data = []
        edges_data = []
        
        # Build query with optional timestamp filter
        timestamp_filter = ""
        params = {"limit": limit}
        
        if since_timestamp:
            timestamp_filter = "WHERE n.created_at > $since"
            params["since"] = since_timestamp
        
        entity_query = f"""
        MATCH (n:Entity)
        {timestamp_filter}
        RETURN n.uuid as id, n.name as label, n.entity_type as type,
               n.created_at as created_at, n.summary as summary
        ORDER BY n.created_at DESC
        LIMIT $limit
        """
        
        async with graph_client.graphiti.driver.session() as session:
            result = await session.run(entity_query, **params)
            async for record in result:
                nodes_data.append(GraphNode(
                    id=record["id"],
                    label=record["label"] or "Unknown",
                    type=record["type"] or "Entity",
                    metadata={
                        "created_at": record.get("created_at").isoformat() if record.get("created_at") else None,
                        "summary": record.get("summary")
                    }
                ))
        
        return GraphVisualizationData(
            nodes=nodes_data,
            edges=edges_data,
            metadata={
                "recent_changes": True,
                "since": since_timestamp.isoformat() if since_timestamp else None
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get recent graph changes: {e}")
        return GraphVisualizationData(nodes=[], edges=[])


def generate_graph_url(
    session_id: Optional[str] = None,
    base_url: Optional[str] = None
) -> str:
    """
    Generate URL for graph visualization.
    
    For now, returns a URL to the graph data endpoint.
    In production, this could point to:
    - Neo4j Browser with pre-configured query
    - Custom graph visualization page
    - Static graph image
    
    Args:
        session_id: Optional session ID
        base_url: Base URL for the API (defaults to env or localhost)
    
    Returns:
        URL string for graph visualization
    """
    if base_url is None:
        base_url = os.getenv("APP_BASE_URL", "http://localhost:8058")
    
    # Return URL to graph data endpoint
    url = f"{base_url}/graph/data"
    
    if session_id:
        url += f"?session_id={session_id}"
    
    return url


async def get_entity_subgraph(
    entity_name: str,
    depth: int = 2,
    limit: int = 30
) -> GraphVisualizationData:
    """
    Get a subgraph centered around a specific entity.
    
    Args:
        entity_name: Name of the central entity
        depth: Maximum traversal depth
        limit: Maximum number of nodes
    
    Returns:
        GraphVisualizationData with subgraph
    """
    if not graph_client or not graph_client._initialized:
        logger.warning("Graph client not initialized")
        return GraphVisualizationData(nodes=[], edges=[])
    
    try:
        nodes_data = []
        edges_data = []
        
        # Query for entity and its neighbors up to specified depth
        subgraph_query = """
        MATCH path = (center:Entity {name: $entity_name})-[*1..$depth]-(neighbor:Entity)
        WITH center, neighbor, relationships(path) as rels
        RETURN DISTINCT center.uuid as center_id, center.name as center_label,
               center.entity_type as center_type,
               neighbor.uuid as neighbor_id, neighbor.name as neighbor_label,
               neighbor.entity_type as neighbor_type,
               [r IN rels | {
                   from: startNode(r).uuid,
                   to: endNode(r).uuid,
                   label: r.relationship_type,
                   fact: r.fact
               }] as edges
        LIMIT $limit
        """
        
        async with graph_client.graphiti.driver.session() as session:
            result = await session.run(
                subgraph_query,
                entity_name=entity_name,
                depth=depth,
                limit=limit
            )
            
            seen_nodes = set()
            
            async for record in result:
                # Add center node
                center_id = record["center_id"]
                if center_id not in seen_nodes:
                    nodes_data.append(GraphNode(
                        id=center_id,
                        label=record["center_label"],
                        type=record["center_type"] or "Entity",
                        metadata={"central": True}
                    ))
                    seen_nodes.add(center_id)
                
                # Add neighbor node
                neighbor_id = record["neighbor_id"]
                if neighbor_id not in seen_nodes:
                    nodes_data.append(GraphNode(
                        id=neighbor_id,
                        label=record["neighbor_label"],
                        type=record["neighbor_type"] or "Entity",
                        metadata={}
                    ))
                    seen_nodes.add(neighbor_id)
                
                # Add edges
                for edge_data in record["edges"]:
                    edges_data.append(GraphEdge(
                        from_node=edge_data["from"],
                        to_node=edge_data["to"],
                        label=edge_data.get("label", "relates_to"),
                        metadata={"fact": edge_data.get("fact")}
                    ))
        
        return GraphVisualizationData(
            nodes=nodes_data,
            edges=edges_data,
            metadata={
                "center_entity": entity_name,
                "depth": depth
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get entity subgraph: {e}")
        return GraphVisualizationData(nodes=[], edges=[])

