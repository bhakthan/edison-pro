"""
Azure AI Search Index Creation for Cognitive Patterns (Memory Atlas)

Creates a dedicated index for storing versioned cognitive patterns from the
Flickering Cognitive Architecture. This index enables semantic similarity search
across all learned patterns with rich metadata filtering.

Separate from the main diagram index - this stores LEARNED PATTERNS, not raw diagrams.
"""

import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
    SemanticConfiguration,
    SemanticPrioritizedFields,
    SemanticField,
    SemanticSearch
)

load_dotenv()


def create_cognitive_patterns_index():
    """
    Create Azure AI Search index for Flickering Cognitive Architecture patterns.
    
    This index stores learned patterns from the Memory Atlas, enabling:
    - Semantic similarity search across learned patterns
    - Version lineage tracking
    - Domain-specific filtering
    - Accuracy and recency-based ranking
    - Cross-instance pattern sharing
    """
    
    # Get credentials from environment
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    search_api_key = os.getenv("AZURE_SEARCH_API_KEY")
    index_name = "edison-cognitive-patterns"
    
    if not search_endpoint or not search_api_key:
        raise ValueError("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_API_KEY must be set in .env")
    
    print(f"🧠 Creating Azure AI Search Index: {index_name}")
    print(f"   Endpoint: {search_endpoint}")
    print()
    
    # Initialize client
    credential = AzureKeyCredential(search_api_key)
    index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
    
    # Define vector search configuration (for feature embeddings)
    vector_search = VectorSearch(
        profiles=[
            VectorSearchProfile(
                name="cognitive-pattern-vector-profile",
                algorithm_configuration_name="cognitive-pattern-hnsw-config"
            )
        ],
        algorithms=[
            HnswAlgorithmConfiguration(
                name="cognitive-pattern-hnsw-config",
                parameters={
                    "m": 4,  # Number of bi-directional links (lower = faster, higher = better recall)
                    "efConstruction": 400,  # Size of dynamic candidate list for construction
                    "efSearch": 500,  # Size of dynamic candidate list for search
                    "metric": "cosine"
                }
            )
        ]
    )
    
    # Define semantic search configuration
    semantic_search = SemanticSearch(
        configurations=[
            SemanticConfiguration(
                name="cognitive-pattern-semantic-config",
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(field_name="pattern_id"),
                    keywords_fields=[
                        SemanticField(field_name="domain"),
                        SemanticField(field_name="contexts")
                    ],
                    content_fields=[
                        SemanticField(field_name="interpretation_summary")
                    ]
                )
            )
        ]
    )
    
    # Define index schema
    fields = [
        # Identity and versioning
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
            filterable=True,
            sortable=True
        ),
        SearchableField(
            name="pattern_id",
            type=SearchFieldDataType.String,
            filterable=True,
            sortable=True
        ),
        SimpleField(
            name="version_id",
            type=SearchFieldDataType.String,
            filterable=True,
            sortable=True
        ),
        SimpleField(
            name="parent_version",
            type=SearchFieldDataType.String,
            filterable=True
        ),
        
        # Feature embedding (512-dimensional vector)
        SearchField(
            name="feature_embedding",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            vector_search_dimensions=512,
            vector_search_profile_name="cognitive-pattern-vector-profile",
            searchable=True
        ),
        
        # Metadata
        SearchableField(
            name="domain",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True
        ),
        SimpleField(
            name="contexts",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            filterable=True,
            facetable=True
        ),
        
        # Quality metrics
        SimpleField(
            name="accuracy",
            type=SearchFieldDataType.Double,
            filterable=True,
            sortable=True
        ),
        SimpleField(
            name="success_count",
            type=SearchFieldDataType.Int32,
            filterable=True,
            sortable=True
        ),
        SimpleField(
            name="confidence_score",
            type=SearchFieldDataType.Double,
            filterable=True,
            sortable=True
        ),
        
        # Temporal
        SimpleField(
            name="timestamp",
            type=SearchFieldDataType.DateTimeOffset,
            filterable=True,
            sortable=True
        ),
        SimpleField(
            name="last_used",
            type=SearchFieldDataType.DateTimeOffset,
            filterable=True,
            sortable=True
        ),
        
        # Interpretation summary (for semantic search)
        SearchableField(
            name="interpretation_summary",
            type=SearchFieldDataType.String,
            analyzer_name="en.microsoft"
        ),
        
        # Component details (JSON array as string)
        SearchableField(
            name="components_json",
            type=SearchFieldDataType.String
        ),
        
        # Full pattern data (for reconstruction)
        SimpleField(
            name="pattern_data_json",
            type=SearchFieldDataType.String
        ),
        
        # Learning provenance
        SimpleField(
            name="source_diagram_id",
            type=SearchFieldDataType.String,
            filterable=True
        ),
        SimpleField(
            name="mismatch_novelty_level",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True
        ),
        
        # Usage statistics
        SimpleField(
            name="retrieval_count",
            type=SearchFieldDataType.Int32,
            filterable=True,
            sortable=True
        ),
        SimpleField(
            name="avg_similarity_on_retrieval",
            type=SearchFieldDataType.Double,
            filterable=True,
            sortable=True
        )
    ]
    
    # Create index
    index = SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search
    )
    
    try:
        # Delete existing index if it exists
        try:
            index_client.delete_index(index_name)
            print(f"🗑️  Deleted existing index: {index_name}")
        except:
            pass
        
        # Create new index
        result = index_client.create_index(index)
        print(f"✅ Successfully created index: {result.name}")
        print()
        print("Index Details:")
        print(f"   Fields: {len(result.fields)}")
        print(f"   Vector dimensions: 512")
        print(f"   Vector similarity: cosine")
        print(f"   Semantic search: enabled")
        print()
        print("Key Features:")
        print("   ✅ Semantic similarity search on 512-dim feature embeddings")
        print("   ✅ Version lineage tracking (parent_version)")
        print("   ✅ Domain-specific filtering (electrical, mechanical, etc.)")
        print("   ✅ Accuracy and confidence-based ranking")
        print("   ✅ Recency-based scoring (timestamp, last_used)")
        print("   ✅ Usage statistics (retrieval_count, avg_similarity)")
        print("   ✅ Mismatch novelty level filtering")
        print()
        print("Next Steps:")
        print("   1. Update MemoryAtlasAgent to use use_vector_db=True")
        print("   2. Run pattern indexing: python index_cognitive_patterns.py")
        print("   3. Test retrieval with similarity search")
        print()
        
        return result
        
    except Exception as e:
        print(f"❌ Error creating index: {e}")
        raise


if __name__ == "__main__":
    print("="*70)
    print("AZURE AI SEARCH - COGNITIVE PATTERNS INDEX CREATION")
    print("="*70)
    print()
    
    try:
        create_cognitive_patterns_index()
        print("="*70)
        print("✅ INDEX CREATION COMPLETE")
        print("="*70)
    except Exception as e:
        print("="*70)
        print("❌ INDEX CREATION FAILED")
        print("="*70)
        print(f"Error: {e}")
        print()
        print("Troubleshooting:")
        print("   1. Verify AZURE_SEARCH_ENDPOINT in .env")
        print("   2. Verify AZURE_SEARCH_API_KEY in .env")
        print("   3. Check Azure Search service is running")
        print("   4. Verify service tier supports vector search")
