"""
Phase 3: Azure AI Search Integration
Cloud-scale pattern storage and semantic search

Author: Srikanth Bhakthan - Microsoft
Date: October 28, 2025
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from azure.search.documents import SearchClient
    from azure.search.documents.indexes import SearchIndexClient
    from azure.search.documents.indexes.models import (
        SearchIndex,
        SimpleField,
        SearchableField,
        SearchField,
        VectorSearch,
        VectorSearchProfile,
        HnswAlgorithmConfiguration
    )
    from azure.core.credentials import AzureKeyCredential
    HAS_AZURE_SEARCH = True
except ImportError:
    HAS_AZURE_SEARCH = False
    logger.warning("⚠️ Azure AI Search SDK not available")


class PatternStorage:
    """
    Azure AI Search integration for storing anomaly patterns,
    expert opinions, and scenario results at cloud scale
    """
    
    def __init__(
        self,
        endpoint: str,
        api_key: str,
        index_name: str = "edison-patterns"
    ):
        if not HAS_AZURE_SEARCH:
            raise ImportError("Azure AI Search SDK required: pip install azure-search-documents")
        
        self.endpoint = endpoint
        self.credential = AzureKeyCredential(api_key)
        self.index_name = index_name
        
        self.index_client = SearchIndexClient(endpoint, self.credential)
        self.search_client = SearchClient(endpoint, index_name, self.credential)
        
        logger.info(f"☁️ Azure AI Search initialized: {index_name}")
    
    def create_index(self):
        """Create search index for patterns"""
        fields = [
            SimpleField(name="id", type="Edm.String", key=True),
            SearchableField(name="pattern_name", type="Edm.String"),
            SearchableField(name="description", type="Edm.String"),
            SimpleField(name="pattern_type", type="Edm.String", filterable=True),
            SimpleField(name="domain", type="Edm.String", filterable=True),
            SimpleField(name="risk_level", type="Edm.String", filterable=True),
            SimpleField(name="effectiveness_score", type="Edm.Double", sortable=True),
            SimpleField(name="times_matched", type="Edm.Int32"),
            SimpleField(name="created_at", type="Edm.DateTimeOffset"),
            SearchableField(name="context", type="Edm.String")
        ]
        
        index = SearchIndex(name=self.index_name, fields=fields)
        self.index_client.create_or_update_index(index)
        logger.info(f"✅ Index created: {self.index_name}")
    
    def upload_pattern(self, pattern: Dict[str, Any]):
        """Upload anomaly pattern to cloud"""
        document = {
            'id': pattern.get('id', f"pattern_{datetime.now().timestamp()}"),
            'pattern_name': pattern.get('name', ''),
            'description': pattern.get('description', ''),
            'pattern_type': pattern.get('type', 'anomaly'),
            'domain': pattern.get('domain', ''),
            'risk_level': pattern.get('risk_level', 'medium'),
            'effectiveness_score': pattern.get('effectiveness', 0.5),
            'times_matched': pattern.get('matches', 0),
            'created_at': datetime.now().isoformat(),
            'context': str(pattern.get('context', {}))
        }
        
        self.search_client.upload_documents([document])
        logger.info(f"📤 Pattern uploaded: {document['pattern_name']}")
    
    def search_patterns(
        self,
        query: str,
        domain: Optional[str] = None,
        pattern_type: Optional[str] = None,
        top: int = 10
    ) -> List[Dict[str, Any]]:
        """Search patterns with filters, using Azure semantic reranker when available."""
        filters = []
        if domain:
            filters.append(f"domain eq '{domain}'")
        if pattern_type:
            filters.append(f"pattern_type eq '{pattern_type}'")

        filter_str = " and ".join(filters) if filters else None

        # Attempt semantic reranking (requires a semantic configuration on the index).
        # Falls back to plain keyword search if the feature is unavailable.
        try:
            from azure.search.documents.models import QueryType
            results = self.search_client.search(
                search_text=query,
                filter=filter_str,
                query_type=QueryType.SEMANTIC,
                semantic_configuration_name="default",
                query_caption="extractive",
                query_answer="extractive",
                top=top,
                include_total_count=True,
            )
            patterns = []
            for r in results:
                doc = dict(r)
                # Prefer the semantic reranker score for ordering; fall back to search score
                doc["_reranker_score"] = r.get("@search.reranker_score", r.get("@search.score", 0.0))
                patterns.append(doc)
            # Sort by reranker score descending so callers get the best results first
            patterns.sort(key=lambda p: p.get("_reranker_score", 0.0), reverse=True)
            logger.info(f"🔍 Found {len(patterns)} patterns (semantic reranked)")
        except Exception as rerank_err:
            # Semantic configuration may not exist on this index — fall back gracefully
            logger.debug(f"Semantic reranking unavailable ({rerank_err}), using keyword search")
            results = self.search_client.search(
                search_text=query,
                filter=filter_str,
                top=top,
                include_total_count=True,
            )
            patterns = [dict(r) for r in results]
            logger.info(f"🔍 Found {len(patterns)} patterns (keyword search)")

        return patterns


def create_pattern_storage(endpoint: str, api_key: str, index_name: str = "edison-patterns"):
    """Factory for pattern storage"""
    return PatternStorage(endpoint, api_key, index_name)
