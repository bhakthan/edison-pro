"""
Author: Srikanth Bhakthan - Microsoft
Azure AI Search Index Creation Script for EDISON/EDISON PRO
Creates the engineering diagrams index with hybrid search capabilities
"""

from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticSearch,
    SemanticPrioritizedFields,
    SemanticField
)
from azure.core.credentials import AzureKeyCredential
import os
from dotenv import load_dotenv

load_dotenv(override=True)

def create_edison_index():
    """Create Azure AI Search index for EDISON engineering diagrams"""
    
    # Load configuration (matching edisonpro.py variable names)
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    search_api_key = os.getenv("AZURE_SEARCH_API_KEY")
    index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "edison-engineering-diagrams")

    if not search_endpoint or not search_api_key:
        raise ValueError("AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_API_KEY must be set in .env")

    print(f"🔧 Creating Azure AI Search Index: {index_name}")
    print(f"   Endpoint: {search_endpoint}")
    
    # Create index client
    credential = AzureKeyCredential(search_api_key)
    index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
    
    # Define fields
    fields = [
        SearchField(
            name="chunk_id",
            type=SearchFieldDataType.String,
            key=True,
            filterable=True
        ),
        SearchField(
            name="content",
            type=SearchFieldDataType.String,
            searchable=True,
            analyzer_name="en.microsoft"
        ),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=1536,
            vector_search_profile_name="vector-profile-1536"
        ),
        SearchField(
            name="page_numbers",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Int32),
            filterable=True,
            facetable=True
        ),
        SearchField(
            name="diagram_type",
            type=SearchFieldDataType.String,
            searchable=True,
            filterable=True,
            facetable=True
        ),
        SearchField(
            name="scale",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True
        ),
        SearchField(
            name="reference_numbers",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            searchable=True,
            filterable=True
        ),
        SearchField(
            name="components",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            searchable=True,
            filterable=True
        ),
        SearchField(
            name="dependencies",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            searchable=True,
            filterable=True
        ),
        SearchField(
            name="source_file",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True
        ),
        SearchField(
            name="timestamp",
            type=SearchFieldDataType.DateTimeOffset,
            filterable=True,
            sortable=True
        )
    ]
    
    # Configure vector search with HNSW algorithm
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="hnsw-algorithm",
                parameters={
                    "m": 4,
                    "efConstruction": 400,
                    "efSearch": 500,
                    "metric": "cosine"
                }
            )
        ],
        profiles=[
            VectorSearchProfile(
                name="vector-profile-1536",
                algorithm_configuration_name="hnsw-algorithm"
            )
        ]
    )
    
    # Configure semantic search (for even better ranking)
    semantic_search = SemanticSearch(
        configurations=[
            SemanticConfiguration(
                name="semantic-config",
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(field_name="diagram_type"),
                    content_fields=[
                        SemanticField(field_name="content")
                    ],
                    keywords_fields=[
                        SemanticField(field_name="components"),
                        SemanticField(field_name="reference_numbers")
                    ]
                )
            )
        ]
    )
    
    # Create the index
    index = SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search
    )
    
    try:
        # Delete if exists (for testing/recreation)
        try:
            index_client.delete_index(index_name)
            print(f"   🗑️  Deleted existing index: {index_name}")
        except:
            pass
        
        # Create new index
        result = index_client.create_index(index)
        print(f"   ✅ Index created successfully: {result.name}")
        print(f"\n📊 Index Configuration:")
        print(f"   • Fields: {len(fields)}")
        print(f"   • Vector Search: HNSW with cosine similarity")
        print(f"   • Vector Dimensions: 1536 (text-embedding-ada-002)")
        print(f"   • Semantic Search: Enabled with prioritized fields")
        print(f"   • Hybrid Search: Ready (vector + keyword)")
        print(f"\n💡 Next Steps:")
        print(f"   1. Add AZURE_SEARCH_* variables to .env")
        print(f"   2. Update ContextManager to use Azure AI Search")
        print(f"   3. Run EDISON/EDISON PRO to populate the index")
        
        return result
        
    except Exception as e:
        print(f"   ❌ Error creating index: {e}")
        raise


if __name__ == "__main__":
    create_edison_index()
