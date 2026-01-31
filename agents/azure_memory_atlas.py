"""
Azure AI Search Integration for Memory Atlas

Extends MemoryAtlasAgent with Azure AI Search capabilities for:
- Semantic similarity search across cognitive patterns
- Cloud-based pattern storage and retrieval
- Cross-instance pattern sharing
- Advanced filtering and ranking
"""

import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import numpy as np
from dotenv import load_dotenv

try:
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient
    from azure.search.documents.models import VectorizedQuery
    AZURE_SEARCH_AVAILABLE = True
except ImportError:
    AZURE_SEARCH_AVAILABLE = False
    print("⚠️  azure-search-documents not installed. Using JSON fallback.")

load_dotenv()


class AzureSearchMemoryAtlas:
    """
    Azure AI Search integration for Memory Atlas cognitive patterns.
    
    Provides semantic similarity search with rich metadata filtering.
    Falls back to JSON storage if Azure Search is unavailable.
    """
    
    def __init__(
        self,
        index_name: str = "edison-cognitive-patterns",
        enable_hybrid: bool = True
    ):
        """
        Initialize Azure Search Memory Atlas
        
        Args:
            index_name: Name of Azure Search index
            enable_hybrid: Keep JSON backup alongside vector DB
        """
        self.index_name = index_name
        self.enable_hybrid = enable_hybrid
        self.search_client = None
        
        # Try to initialize Azure Search
        if AZURE_SEARCH_AVAILABLE:
            try:
                endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
                api_key = os.getenv("AZURE_SEARCH_API_KEY")
                
                if endpoint and api_key:
                    credential = AzureKeyCredential(api_key)
                    self.search_client = SearchClient(
                        endpoint=endpoint,
                        index_name=index_name,
                        credential=credential
                    )
                    print(f"✅ Azure AI Search connected: {index_name}")
                else:
                    print("⚠️  Azure Search credentials not found in .env")
            except Exception as e:
                print(f"⚠️  Azure Search initialization failed: {e}")
                self.search_client = None
    
    def is_available(self) -> bool:
        """Check if Azure Search is available"""
        return self.search_client is not None
    
    def store_pattern(
        self,
        pattern_id: str,
        version_id: str,
        feature_embedding: np.ndarray,
        domain: str,
        components: List[Dict],
        accuracy: float,
        contexts: List[str],
        parent_version: Optional[str] = None,
        confidence_score: float = 1.0,
        source_diagram_id: Optional[str] = None,
        mismatch_novelty_level: Optional[str] = None,
        interpretation_summary: str = ""
    ) -> bool:
        """
        Store cognitive pattern in Azure Search
        
        Args:
            pattern_id: Unique pattern identifier
            version_id: Version identifier (e.g., "v1", "v2")
            feature_embedding: 512-dim feature vector
            domain: Domain (electrical, mechanical, etc.)
            components: List of detected components
            accuracy: Pattern accuracy [0, 1]
            contexts: Usage contexts
            parent_version: Parent version ID for lineage
            confidence_score: Confidence score [0, 1]
            source_diagram_id: Source diagram identifier
            mismatch_novelty_level: Novelty level (low, medium, high, critical)
            interpretation_summary: Human-readable interpretation
        
        Returns:
            True if stored successfully
        """
        if not self.is_available():
            return False
        
        try:
            # Create unique document ID
            doc_id = f"{pattern_id}_{version_id}".replace("/", "_").replace(" ", "_")
            
            # Convert feature embedding to list
            if isinstance(feature_embedding, np.ndarray):
                feature_list = feature_embedding.tolist()
            else:
                feature_list = list(feature_embedding)
            
            # Ensure contexts is a list of strings
            contexts_list = [str(ctx) for ctx in contexts] if contexts else []
            
            # Prepare document with explicit type conversions
            document = {
                "id": str(doc_id),
                "pattern_id": str(pattern_id),
                "version_id": str(version_id),
                "parent_version": str(parent_version) if parent_version else None,
                "feature_embedding": feature_list,
                "domain": str(domain),
                "contexts": contexts_list,
                "accuracy": float(accuracy),
                "success_count": int(1),
                "confidence_score": float(confidence_score),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "last_used": datetime.now(timezone.utc).isoformat(),
                "interpretation_summary": str(interpretation_summary),
                "components_json": json.dumps(components) if components else "[]",
                "pattern_data_json": json.dumps({
                    "pattern_id": pattern_id,
                    "version_id": version_id,
                    "features": feature_list,
                    "domain": domain,
                    "components": components,
                    "accuracy": float(accuracy),
                    "contexts": contexts_list
                }),
                "source_diagram_id": str(source_diagram_id) if source_diagram_id else "",
                "mismatch_novelty_level": str(mismatch_novelty_level) if mismatch_novelty_level else "unknown",
                "retrieval_count": int(0),
                "avg_similarity_on_retrieval": float(0.0)
            }
            
            # Debug: Print document structure
            # print(f"DEBUG: Document fields: {list(document.keys())}")
            # print(f"DEBUG: Contexts type: {type(document['contexts'])}, value: {document['contexts']}")
            
            # Upload document
            result = self.search_client.upload_documents([document])
            
            if result[0].succeeded:
                print(f"✅ Stored pattern in Azure Search: {doc_id}")
                return True
            else:
                error_msg = result[0].error_message if hasattr(result[0], 'error_message') else str(result[0])
                print(f"⚠️  Failed to store pattern: {error_msg}")
                print(f"DEBUG: Document keys: {list(document.keys())}")
                print(f"DEBUG: Contexts: {document['contexts']} (type: {type(document['contexts'])})")
                print(f"DEBUG: Feature embedding: {type(document['feature_embedding'])}, len: {len(document['feature_embedding'])}")
                return False
                
        except Exception as e:
            print(f"❌ Error storing pattern in Azure Search: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def retrieve_similar(
        self,
        query_embedding: np.ndarray,
        domain: Optional[str] = None,
        top_k: int = 5,
        min_accuracy: float = 0.0,
        max_age_days: Optional[int] = None,
        contexts: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve similar patterns using vector similarity search
        
        Args:
            query_embedding: 512-dim query vector
            domain: Filter by domain (optional)
            top_k: Number of results to return
            min_accuracy: Minimum accuracy threshold
            max_age_days: Maximum age in days (optional)
            contexts: Filter by contexts (optional)
        
        Returns:
            List of matching patterns with similarity scores
        """
        if not self.is_available():
            return []
        
        try:
            # Create vector query
            vector_query = VectorizedQuery(
                vector=query_embedding.tolist(),
                k_nearest_neighbors=top_k * 2,  # Get extra for filtering
                fields="feature_embedding"
            )
            
            # Build filter string
            filters = []
            if domain:
                filters.append(f"domain eq '{domain}'")
            if min_accuracy > 0:
                filters.append(f"accuracy ge {min_accuracy}")
            if max_age_days:
                cutoff = datetime.now(timezone.utc).replace(
                    day=datetime.now(timezone.utc).day - max_age_days
                )
                filters.append(f"timestamp ge {cutoff.isoformat()}")
            
            filter_str = " and ".join(filters) if filters else None
            
            # Execute search
            results = self.search_client.search(
                search_text=None,
                vector_queries=[vector_query],
                filter=filter_str,
                select=[
                    "pattern_id", "version_id", "parent_version",
                    "domain", "contexts", "accuracy", "confidence_score",
                    "timestamp", "components_json", "pattern_data_json",
                    "success_count", "interpretation_summary"
                ],
                top=top_k
            )
            
            # Process results
            patterns = []
            for result in results:
                try:
                    # Parse JSON fields
                    components = json.loads(result.get("components_json", "[]"))
                    pattern_data = json.loads(result.get("pattern_data_json", "{}"))
                    
                    patterns.append({
                        "pattern_id": result["pattern_id"],
                        "version_id": result["version_id"],
                        "parent_version": result.get("parent_version"),
                        "domain": result["domain"],
                        "contexts": result.get("contexts", []),
                        "accuracy": result["accuracy"],
                        "confidence_score": result.get("confidence_score", 1.0),
                        "timestamp": result["timestamp"],
                        "components": components,
                        "pattern_data": pattern_data,
                        "success_count": result.get("success_count", 0),
                        "interpretation_summary": result.get("interpretation_summary", ""),
                        "similarity_score": result.get("@search.score", 0.0),
                        "source": "azure_search"
                    })
                except Exception as e:
                    print(f"⚠️  Error parsing result: {e}")
                    continue
            
            print(f"🔍 Retrieved {len(patterns)} patterns from Azure Search")
            return patterns[:top_k]
            
        except Exception as e:
            print(f"❌ Error retrieving from Azure Search: {e}")
            return []
    
    def update_usage_stats(
        self,
        pattern_id: str,
        version_id: str,
        similarity_score: float
    ) -> bool:
        """
        Update pattern usage statistics after retrieval
        
        Args:
            pattern_id: Pattern identifier
            version_id: Version identifier
            similarity_score: Similarity score from retrieval
        
        Returns:
            True if updated successfully
        """
        if not self.is_available():
            return False
        
        try:
            doc_id = f"{pattern_id}_{version_id}".replace("/", "_").replace(" ", "_")
            
            # Retrieve current document
            result = self.search_client.get_document(key=doc_id)
            
            # Update stats
            current_count = result.get("retrieval_count", 0)
            current_avg = result.get("avg_similarity_on_retrieval", 0.0)
            
            new_count = current_count + 1
            new_avg = (current_avg * current_count + similarity_score) / new_count
            
            # Update document
            update_doc = {
                "id": doc_id,
                "retrieval_count": new_count,
                "avg_similarity_on_retrieval": new_avg,
                "last_used": datetime.now(timezone.utc).isoformat()
            }
            
            result = self.search_client.merge_documents([update_doc])
            
            if result[0].succeeded:
                return True
            else:
                print(f"⚠️  Failed to update usage stats: {result[0].error_message}")
                return False
                
        except Exception as e:
            print(f"❌ Error updating usage stats: {e}")
            return False
    
    def get_pattern_lineage(
        self,
        pattern_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get version lineage for a pattern (like git log)
        
        Args:
            pattern_id: Pattern identifier
        
        Returns:
            List of versions in chronological order
        """
        if not self.is_available():
            return []
        
        try:
            results = self.search_client.search(
                search_text=None,
                filter=f"pattern_id eq '{pattern_id}'",
                order_by="timestamp asc",
                select=[
                    "version_id", "parent_version", "timestamp",
                    "accuracy", "confidence_score", "interpretation_summary"
                ]
            )
            
            lineage = []
            for result in results:
                lineage.append({
                    "version_id": result["version_id"],
                    "parent_version": result.get("parent_version"),
                    "timestamp": result["timestamp"],
                    "accuracy": result["accuracy"],
                    "confidence_score": result.get("confidence_score", 1.0),
                    "interpretation_summary": result.get("interpretation_summary", "")
                })
            
            return lineage
            
        except Exception as e:
            print(f"❌ Error getting lineage: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get Memory Atlas statistics from Azure Search"""
        if not self.is_available():
            return {"available": False}
        
        try:
            # Get total count
            results = self.search_client.search(
                search_text="*",
                include_total_count=True,
                top=0
            )
            
            total_patterns = results.get_count()
            
            # Get domain distribution
            domain_facets = self.search_client.search(
                search_text="*",
                facets=["domain"],
                top=0
            )
            
            domains = {}
            for facet in domain_facets.get_facets().get("domain", []):
                domains[facet["value"]] = facet["count"]
            
            return {
                "available": True,
                "total_patterns": total_patterns,
                "domain_distribution": domains,
                "index_name": self.index_name
            }
            
        except Exception as e:
            print(f"❌ Error getting statistics: {e}")
            return {"available": False, "error": str(e)}


# Convenience function for easy integration
def create_azure_memory_atlas(
    index_name: str = "edison-cognitive-patterns"
) -> Optional[AzureSearchMemoryAtlas]:
    """
    Create Azure Search Memory Atlas instance
    
    Returns None if Azure Search is not available
    """
    atlas = AzureSearchMemoryAtlas(index_name=index_name)
    return atlas if atlas.is_available() else None
