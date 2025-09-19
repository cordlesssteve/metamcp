#!/usr/bin/env python3
"""
Ingestion Pipeline for MetaMCP RAG Tool Retriever

This script indexes all available MCP tools into a ChromaDB vector database
for efficient semantic retrieval during agent execution.

Usage:
    python ingest.py --tools-source /path/to/tools --persist-dir ./chroma_db
    python ingest.py --metamcp-tools /path/to/metamcp/tools.json
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# ChromaDB and LangChain imports
try:
    from langchain.embeddings import HuggingFaceEmbeddings
    from langchain.vectorstores import Chroma
    from langchain.docstore.document import Document
except ImportError as e:
    print(f"Error: Required packages not installed. Run: pip install langchain chromadb sentence-transformers")
    print(f"Import error: {e}")
    sys.exit(1)

# Local imports
from tool_definitions import ToolStandardizer, create_sample_tools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ToolIngestionPipeline:
    """Pipeline for ingesting tools into ChromaDB for RAG retrieval"""

    def __init__(self, persist_directory: str = "./chroma_db"):
        """
        Initialize the ingestion pipeline

        Args:
            persist_directory: Directory to store the ChromaDB database
        """
        self.persist_directory = persist_directory
        self.embedding_model = None
        self.vector_store = None
        self.standardizer = ToolStandardizer()

        # Ensure persist directory exists
        Path(persist_directory).mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized ingestion pipeline with persist directory: {persist_directory}")

    def _init_embeddings(self) -> HuggingFaceEmbeddings:
        """Initialize the embedding model"""
        if self.embedding_model is None:
            logger.info("Initializing nomic-embed-text-v1.5 embedding model...")

            try:
                self.embedding_model = HuggingFaceEmbeddings(
                    model_name="nomic-ai/nomic-embed-text-v1.5",
                    model_kwargs={'trust_remote_code': True}
                )
                logger.info("Successfully initialized embedding model")
            except Exception as e:
                logger.error(f"Failed to initialize embedding model: {e}")
                logger.info("Falling back to sentence-transformers/all-MiniLM-L6-v2")
                self.embedding_model = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/all-MiniLM-L6-v2"
                )

        return self.embedding_model

    def load_tools_from_metamcp_json(self, json_file_path: str) -> None:
        """
        Load tools from a metaMCP tools JSON file

        Args:
            json_file_path: Path to JSON file containing tool definitions
        """
        logger.info(f"Loading tools from metaMCP JSON file: {json_file_path}")

        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                tools_data = json.load(f)

            if isinstance(tools_data, list):
                self.standardizer.load_from_metamcp_format(tools_data)
            elif isinstance(tools_data, dict) and 'tools' in tools_data:
                self.standardizer.load_from_metamcp_format(tools_data['tools'])
            else:
                raise ValueError("JSON file must contain a list of tools or an object with 'tools' key")

            logger.info(f"Successfully loaded {len(self.standardizer.tools)} tools from JSON")

        except Exception as e:
            logger.error(f"Error loading tools from JSON file: {e}")
            raise

    def load_tools_from_directory(self, tools_directory: str) -> None:
        """
        Load tools from a directory containing tool definitions

        Args:
            tools_directory: Directory containing tool definition files
        """
        logger.info(f"Loading tools from directory: {tools_directory}")

        tools_path = Path(tools_directory)
        if not tools_path.exists():
            raise ValueError(f"Tools directory does not exist: {tools_directory}")

        tool_files = list(tools_path.glob("*.json"))
        if not tool_files:
            logger.warning(f"No JSON tool files found in {tools_directory}")
            return

        for tool_file in tool_files:
            try:
                with open(tool_file, 'r', encoding='utf-8') as f:
                    tool_data = json.load(f)

                if isinstance(tool_data, list):
                    for tool in tool_data:
                        self.standardizer.add_mcp_tool(tool, tool_file.stem)
                elif isinstance(tool_data, dict):
                    self.standardizer.add_mcp_tool(tool_data, tool_file.stem)

                logger.info(f"Loaded tools from {tool_file.name}")

            except Exception as e:
                logger.error(f"Error loading tools from {tool_file}: {e}")

        logger.info(f"Successfully loaded {len(self.standardizer.tools)} tools from directory")

    def load_sample_tools(self) -> None:
        """Load sample tools for testing"""
        logger.info("Loading sample tools for testing...")
        sample_tools = create_sample_tools()
        self.standardizer.tools.extend(sample_tools)
        logger.info(f"Loaded {len(sample_tools)} sample tools")

    def create_vector_store(self, collection_name: str = "metamcp_tools") -> None:
        """
        Create and populate the ChromaDB vector store

        Args:
            collection_name: Name for the ChromaDB collection
        """
        if not self.standardizer.tools:
            raise ValueError("No tools loaded. Please load tools before creating vector store.")

        logger.info(f"Creating vector store with {len(self.standardizer.tools)} tools...")

        # Initialize embeddings
        embeddings = self._init_embeddings()

        # Get tool descriptions and metadata
        descriptions = self.standardizer.get_tool_descriptions()
        metadata = self.standardizer.get_tool_metadata()

        # Create documents for ChromaDB
        documents = []
        metadatas = []

        for i, (desc, meta) in enumerate(zip(descriptions, metadata)):
            documents.append(desc)
            metadatas.append({
                **meta,
                "tool_index": i,
                "collection": collection_name
            })

        logger.info("Creating ChromaDB vector store...")

        try:
            # Create the vector store
            self.vector_store = Chroma.from_texts(
                texts=documents,
                embedding=embeddings,
                metadatas=metadatas,
                persist_directory=self.persist_directory,
                collection_name=collection_name
            )

            # Persist the database
            self.vector_store.persist()
            logger.info(f"Successfully created and persisted vector store at {self.persist_directory}")

        except Exception as e:
            logger.error(f"Error creating vector store: {e}")
            raise

    def update_vector_store(self, new_tools: List[Dict[str, Any]],
                          collection_name: str = "metamcp_tools") -> None:
        """
        Update existing vector store with new tools

        Args:
            new_tools: List of new tool definitions to add
            collection_name: Name of the ChromaDB collection
        """
        logger.info(f"Updating vector store with {len(new_tools)} new tools...")

        # Load new tools into standardizer
        original_count = len(self.standardizer.tools)
        for tool_data in new_tools:
            self.standardizer.add_mcp_tool(tool_data, "Updated Tools")

        new_count = len(self.standardizer.tools) - original_count
        logger.info(f"Added {new_count} new standardized tools")

        # Get only the new tool descriptions and metadata
        new_descriptions = self.standardizer.get_tool_descriptions()[-new_count:]
        new_metadata = self.standardizer.get_tool_metadata()[-new_count:]

        # Initialize embeddings if not already done
        embeddings = self._init_embeddings()

        # Load existing vector store or create new one
        try:
            if os.path.exists(os.path.join(self.persist_directory, "chroma.sqlite3")):
                self.vector_store = Chroma(
                    persist_directory=self.persist_directory,
                    embedding_function=embeddings,
                    collection_name=collection_name
                )
                logger.info("Loaded existing vector store")
            else:
                logger.info("No existing vector store found, creating new one")
                self.create_vector_store(collection_name)
                return

            # Add new documents
            new_metadatas = []
            for i, meta in enumerate(new_metadata):
                new_metadatas.append({
                    **meta,
                    "tool_index": original_count + i,
                    "collection": collection_name
                })

            self.vector_store.add_texts(
                texts=new_descriptions,
                metadatas=new_metadatas
            )

            # Persist changes
            self.vector_store.persist()
            logger.info("Successfully updated vector store")

        except Exception as e:
            logger.error(f"Error updating vector store: {e}")
            raise

    def get_database_stats(self) -> Dict[str, Any]:
        """Get statistics about the created database"""
        if not self.vector_store:
            return {"error": "Vector store not created"}

        try:
            # Get collection info
            collection = self.vector_store._collection
            count = collection.count()

            return {
                "total_tools": len(self.standardizer.tools),
                "documents_in_db": count,
                "persist_directory": self.persist_directory,
                "embedding_model": getattr(self.embedding_model, 'model_name', 'unknown'),
                "collection_name": collection.name
            }
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {"error": str(e)}

    def export_tool_manifest(self, output_file: str) -> None:
        """
        Export a manifest of all indexed tools

        Args:
            output_file: Path to write the tool manifest JSON
        """
        manifest = {
            "metadata": {
                "total_tools": len(self.standardizer.tools),
                "persist_directory": self.persist_directory,
                "embedding_model": getattr(self.embedding_model, 'model_name', 'unknown'),
                "created_at": None  # Will be set by JSON serializer
            },
            "tools": []
        }

        for tool in self.standardizer.tools:
            manifest["tools"].append({
                "name": tool.name,
                "server_source": tool.server_source,
                "description_preview": tool.description[:200] + "..." if len(tool.description) > 200 else tool.description,
                "has_parameters": bool(tool.original_schema.get('inputSchema', {}).get('properties', {}))
            })

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        logger.info(f"Exported tool manifest to {output_file}")

def main():
    """Main entry point for the ingestion pipeline"""
    parser = argparse.ArgumentParser(
        description="Ingest MCP tools into ChromaDB for RAG retrieval"
    )

    # Input sources (mutually exclusive)
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--tools-directory",
        help="Directory containing tool definition JSON files"
    )
    source_group.add_argument(
        "--metamcp-tools",
        help="Path to metaMCP tools JSON file"
    )
    source_group.add_argument(
        "--sample-tools",
        action="store_true",
        help="Use sample tools for testing"
    )

    # Output configuration
    parser.add_argument(
        "--persist-dir",
        default="./chroma_db",
        help="Directory to store ChromaDB database (default: ./chroma_db)"
    )
    parser.add_argument(
        "--collection-name",
        default="metamcp_tools",
        help="ChromaDB collection name (default: metamcp_tools)"
    )

    # Optional features
    parser.add_argument(
        "--export-manifest",
        help="Export tool manifest to JSON file"
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update existing database instead of creating new one"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize pipeline
    pipeline = ToolIngestionPipeline(args.persist_dir)

    try:
        # Load tools based on source
        if args.sample_tools:
            pipeline.load_sample_tools()
        elif args.metamcp_tools:
            pipeline.load_tools_from_metamcp_json(args.metamcp_tools)
        elif args.tools_directory:
            pipeline.load_tools_from_directory(args.tools_directory)

        # Create or update vector store
        if args.update:
            logger.info("Update mode not fully implemented - creating new vector store")
            pipeline.create_vector_store(args.collection_name)
        else:
            pipeline.create_vector_store(args.collection_name)

        # Print statistics
        stats = pipeline.get_database_stats()
        logger.info("Database Statistics:")
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")

        # Export manifest if requested
        if args.export_manifest:
            pipeline.export_tool_manifest(args.export_manifest)

        logger.info("Ingestion pipeline completed successfully!")

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()