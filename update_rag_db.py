#!/usr/bin/env python3
"""
Update RAG database with test server tools
"""
import os
import sys
import json
from pathlib import Path

# Add the rag-tool-retriever to Python path
sys.path.append(str(Path(__file__).parent / "rag-tool-retriever"))

from retriever import ToolRetriever
from tool_definitions import ToolStandardizer

# Test server tools
test_tools = [
    # TEST1 - File Operations
    {"name": "test_read_file", "description": "Read a test file from the filesystem"},
    {"name": "test_write_file", "description": "Write content to a test file"},
    {"name": "test_list_files", "description": "List test files in directory"},

    # TEST2 - Math Calculations
    {"name": "test_calculate", "description": "Perform mathematical calculations"},
    {"name": "test_convert_units", "description": "Convert between different units"},
    {"name": "test_statistics", "description": "Calculate statistics on a dataset"},

    # TEST3 - Text Processing
    {"name": "test_format_text", "description": "Format and style text content"},
    {"name": "test_extract_keywords", "description": "Extract keywords from text"},
    {"name": "test_summarize", "description": "Summarize text content"},

    # TEST4 - Data Generation
    {"name": "test_generate_data", "description": "Generate test data sets"},
    {"name": "test_create_sample", "description": "Create sample configuration or template"},
    {"name": "test_mock_api", "description": "Generate mock API responses"},

    # TEST5 - System Info
    {"name": "test_system_status", "description": "Check system status and health"},
    {"name": "test_environment", "description": "Get environment information"},
    {"name": "test_diagnostics", "description": "Run system diagnostics"},
]

def main():
    print("🔄 Updating RAG database with test server tools...")

    # Initialize components
    persist_dir = "rag-tool-retriever/real_tools_db"
    retriever = ToolRetriever(persist_directory=persist_dir, collection_name="tool_collection")
    standardizer = ToolStandardizer()

    # Clear existing collection and add test tools
    try:
        # Clear the collection
        retriever.vectorstore._collection.delete()
        print("✓ Cleared existing tool collection")

        # Standardize and add test tools
        standardized_tools = [standardizer.standardize_tool(tool) for tool in test_tools]

        # Add to vector database
        for tool in standardized_tools:
            document_text = f"{tool['name']}: {tool['description']}"
            retriever.vectorstore.add_texts(
                texts=[document_text],
                metadatas=[tool],
                ids=[tool['name']]
            )

        print(f"✓ Added {len(test_tools)} test tools to RAG database")

        # Test the database
        test_query = "calculate mathematical expressions"
        results = retriever.vectorstore.similarity_search(test_query, k=3)
        print(f"✓ Test query '{test_query}' returned {len(results)} results")
        for result in results:
            print(f"  - {result.metadata.get('name', 'Unknown')}: {result.page_content}")

    except Exception as e:
        print(f"❌ Error updating RAG database: {e}")
        return 1

    print("🎉 RAG database updated successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())