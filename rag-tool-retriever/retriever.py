"""
Tool Retriever Module for MetaMCP RAG System

This module provides dynamic tool retrieval based on semantic similarity
to user queries, replacing static tool loading with intelligent selection.
"""

import logging
import os
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

# ChromaDB and LangChain imports
try:
    from langchain.embeddings import HuggingFaceEmbeddings
    from langchain.vectorstores import Chroma
    from langchain.tools import Tool
    from langchain.docstore.document import Document
except ImportError as e:
    raise ImportError(
        f"Required packages not installed. Run: pip install langchain chromadb sentence-transformers\n"
        f"Import error: {e}"
    )

# Local imports
from tool_definitions import ToolStandardizer

# Configure logging
logger = logging.getLogger(__name__)

class ToolRetriever:
    """
    Dynamic tool retriever using semantic similarity for metaMCP agents

    This class provides the core functionality to retrieve relevant tools
    based on user queries, dramatically reducing context window usage.
    """

    def __init__(self, persist_directory: str = "./chroma_db",
                 collection_name: str = "metamcp_tools",
                 default_k: int = 5):
        """
        Initialize the tool retriever

        Args:
            persist_directory: Directory containing the ChromaDB database
            collection_name: Name of the ChromaDB collection
            default_k: Default number of tools to retrieve
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.default_k = default_k
        self.embedding_model = None
        self.vector_store = None
        self.tool_registry = {}  # Maps tool names to actual tool objects
        self.fallback_tools = []  # Core tools for fallback

        # Validate database exists
        self._validate_database()

        logger.info(f"Initialized ToolRetriever with database at {persist_directory}")

    def _validate_database(self) -> None:
        """Validate that the ChromaDB database exists"""
        db_path = Path(self.persist_directory)
        if not db_path.exists():
            raise ValueError(f"Database directory does not exist: {self.persist_directory}")

        # Check for ChromaDB files
        expected_files = ["chroma.sqlite3"]
        missing_files = [f for f in expected_files
                        if not (db_path / f).exists()]

        if missing_files:
            logger.warning(f"Database may be incomplete. Missing files: {missing_files}")

    def _init_embeddings(self) -> HuggingFaceEmbeddings:
        """Initialize the same embedding model used for ingestion"""
        if self.embedding_model is None:
            logger.debug("Initializing embedding model for retrieval...")

            try:
                self.embedding_model = HuggingFaceEmbeddings(
                    model_name="nomic-ai/nomic-embed-text-v1.5",
                    model_kwargs={'trust_remote_code': True}
                )
            except Exception as e:
                logger.warning(f"Failed to load nomic-embed-text-v1.5: {e}")
                logger.info("Falling back to sentence-transformers/all-MiniLM-L6-v2")
                self.embedding_model = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/all-MiniLM-L6-v2"
                )

        return self.embedding_model

    def _load_vector_store(self) -> Chroma:
        """Load the existing ChromaDB vector store"""
        if self.vector_store is None:
            logger.debug("Loading ChromaDB vector store...")

            embeddings = self._init_embeddings()

            try:
                self.vector_store = Chroma(
                    persist_directory=self.persist_directory,
                    embedding_function=embeddings,
                    collection_name=self.collection_name
                )
                logger.debug("Successfully loaded vector store")

            except Exception as e:
                logger.error(f"Failed to load vector store: {e}")
                raise

        return self.vector_store

    def register_tools(self, tools: List[Tool]) -> None:
        """
        Register actual tool objects for retrieval

        Args:
            tools: List of LangChain Tool objects to register
        """
        self.tool_registry.clear()
        for tool in tools:
            self.tool_registry[tool.name] = tool

        logger.info(f"Registered {len(tools)} tools in registry")

    def set_fallback_tools(self, tools: List[Tool]) -> None:
        """
        Set fallback tools (core filesystem/basic tools)

        Args:
            tools: List of essential tools to use when retrieval fails
        """
        self.fallback_tools = tools
        logger.info(f"Set {len(tools)} fallback tools")

    def get_relevant_tools(self, query: str, k: Optional[int] = None,
                          score_threshold: float = 0.0) -> List[Tool]:
        """
        Retrieve tools most relevant to the given query

        Args:
            query: User query or task description
            k: Number of tools to retrieve (defaults to self.default_k)
            score_threshold: Minimum similarity score for inclusion

        Returns:
            List of relevant LangChain Tool objects
        """
        if k is None:
            k = self.default_k

        logger.debug(f"Retrieving {k} tools for query: '{query[:100]}...'")

        try:
            vector_store = self._load_vector_store()

            # Create retriever with specified parameters
            retriever = vector_store.as_retriever(
                search_type="similarity_score_threshold",
                search_kwargs={
                    "k": k,
                    "score_threshold": score_threshold
                }
            )

            # Retrieve relevant documents
            relevant_docs = retriever.get_relevant_documents(query)

            if not relevant_docs:
                logger.warning(f"No tools found for query: '{query}'. Using fallback tools.")
                return self.fallback_tools[:k]

            # Extract tool names from metadata and get actual tool objects
            retrieved_tools = []
            tool_names_found = []

            for doc in relevant_docs:
                tool_name = doc.metadata.get('name')
                if tool_name and tool_name in self.tool_registry:
                    tool = self.tool_registry[tool_name]
                    retrieved_tools.append(tool)
                    tool_names_found.append(tool_name)

            logger.debug(f"Retrieved {len(retrieved_tools)} tools: {tool_names_found}")

            # If we didn't get enough tools, pad with fallback tools
            if len(retrieved_tools) < k and self.fallback_tools:
                needed = k - len(retrieved_tools)
                fallback_to_add = [t for t in self.fallback_tools
                                 if t.name not in tool_names_found][:needed]
                retrieved_tools.extend(fallback_to_add)
                logger.debug(f"Added {len(fallback_to_add)} fallback tools")

            return retrieved_tools

        except Exception as e:
            logger.error(f"Error during tool retrieval: {e}")
            logger.info("Falling back to default tools")
            return self.fallback_tools[:k]

    def get_tools_with_scores(self, query: str, k: Optional[int] = None) -> List[Tuple[Tool, float]]:
        """
        Retrieve tools with their similarity scores

        Args:
            query: User query or task description
            k: Number of tools to retrieve

        Returns:
            List of (Tool, score) tuples sorted by relevance
        """
        if k is None:
            k = self.default_k

        try:
            vector_store = self._load_vector_store()

            # Get documents with scores
            docs_with_scores = vector_store.similarity_search_with_score(query, k=k)

            tools_with_scores = []
            for doc, score in docs_with_scores:
                tool_name = doc.metadata.get('name')
                if tool_name and tool_name in self.tool_registry:
                    tool = self.tool_registry[tool_name]
                    tools_with_scores.append((tool, score))

            return tools_with_scores

        except Exception as e:
            logger.error(f"Error retrieving tools with scores: {e}")
            return [(tool, 0.0) for tool in self.fallback_tools[:k]]

    def search_tools_by_keywords(self, keywords: List[str], k: Optional[int] = None) -> List[Tool]:
        """
        Search for tools by specific keywords

        Args:
            keywords: List of keywords to search for
            k: Number of tools to retrieve

        Returns:
            List of relevant tools
        """
        # Combine keywords into a search query
        query = " ".join(keywords)
        return self.get_relevant_tools(query, k)

    def get_tool_by_name(self, tool_name: str) -> Optional[Tool]:
        """
        Get a specific tool by name

        Args:
            tool_name: Name of the tool to retrieve

        Returns:
            Tool object if found, None otherwise
        """
        return self.tool_registry.get(tool_name)

    def get_all_available_tools(self) -> List[Tool]:
        """Get all registered tools"""
        return list(self.tool_registry.values())

    def get_database_info(self) -> Dict[str, Any]:
        """Get information about the loaded database"""
        try:
            vector_store = self._load_vector_store()
            collection = vector_store._collection

            return {
                "collection_name": self.collection_name,
                "persist_directory": self.persist_directory,
                "total_documents": collection.count(),
                "registered_tools": len(self.tool_registry),
                "fallback_tools": len(self.fallback_tools),
                "embedding_model": getattr(self.embedding_model, 'model_name', 'unknown')
            }
        except Exception as e:
            return {"error": str(e)}

    def explain_retrieval(self, query: str, k: int = 5) -> Dict[str, Any]:
        """
        Explain why specific tools were retrieved for a query

        Args:
            query: User query
            k: Number of tools to analyze

        Returns:
            Dictionary with retrieval explanation
        """
        try:
            tools_with_scores = self.get_tools_with_scores(query, k)

            explanation = {
                "query": query,
                "retrieved_tools": [],
                "retrieval_strategy": "semantic_similarity",
                "embedding_model": getattr(self.embedding_model, 'model_name', 'unknown')
            }

            for tool, score in tools_with_scores:
                explanation["retrieved_tools"].append({
                    "name": tool.name,
                    "score": float(score),
                    "description_preview": tool.description[:150] + "..."
                })

            return explanation

        except Exception as e:
            return {"error": str(e), "query": query}

class MetaMCPToolRetriever(ToolRetriever):
    """
    Specialized tool retriever for metaMCP integration

    This class extends the base retriever with metaMCP-specific functionality
    including tool mapping and server-aware retrieval.
    """

    def __init__(self, persist_directory: str = "./chroma_db",
                 collection_name: str = "metamcp_tools",
                 default_k: int = 5):
        super().__init__(persist_directory, collection_name, default_k)
        self.tool_to_server_mapping = {}  # Maps tool names to server UUIDs

    def register_metamcp_tools(self, tools_data: List[Dict[str, Any]],
                              tool_to_client_mapping: Dict[str, Any]) -> None:
        """
        Register tools from metaMCP with server mapping

        Args:
            tools_data: List of tool definitions from metaMCP
            tool_to_client_mapping: Mapping of tool names to client connections
        """
        from tool_definitions import ToolStandardizer

        standardizer = ToolStandardizer()
        standardizer.load_from_metamcp_format(tools_data)

        # Convert to LangChain tools and register
        langchain_tools = standardizer.get_langchain_tools()
        self.register_tools(langchain_tools)

        # Store server mapping
        for tool_name, client in tool_to_client_mapping.items():
            self.tool_to_server_mapping[tool_name] = client

        logger.info(f"Registered {len(langchain_tools)} metaMCP tools with server mapping")

    def get_relevant_tools_with_servers(self, query: str, k: Optional[int] = None) -> List[Tuple[Tool, Any]]:
        """
        Get relevant tools along with their server connections

        Args:
            query: User query
            k: Number of tools to retrieve

        Returns:
            List of (Tool, server_client) tuples
        """
        relevant_tools = self.get_relevant_tools(query, k)
        tools_with_servers = []

        for tool in relevant_tools:
            server_client = self.tool_to_server_mapping.get(tool.name)
            tools_with_servers.append((tool, server_client))

        return tools_with_servers

    def get_tools_by_server(self, server_name: str) -> List[Tool]:
        """
        Get all tools from a specific server

        Args:
            server_name: Name of the server

        Returns:
            List of tools from that server
        """
        # This would need to be implemented based on metaMCP's server identification
        # For now, return empty list
        return []

# Utility functions for easy integration

def create_retriever_from_database(persist_directory: str = "./chroma_db",
                                  collection_name: str = "metamcp_tools",
                                  fallback_tools: List[Tool] = None) -> ToolRetriever:
    """
    Create a configured tool retriever from an existing database

    Args:
        persist_directory: Path to ChromaDB database
        collection_name: ChromaDB collection name
        fallback_tools: List of fallback tools

    Returns:
        Configured ToolRetriever instance
    """
    retriever = ToolRetriever(persist_directory, collection_name)

    if fallback_tools:
        retriever.set_fallback_tools(fallback_tools)

    return retriever

def get_relevant_tools(query: str, persist_directory: str = "./chroma_db",
                      k: int = 5) -> List[Tool]:
    """
    Quick function to get relevant tools for a query

    Args:
        query: User query
        persist_directory: Path to ChromaDB database
        k: Number of tools to retrieve

    Returns:
        List of relevant tools
    """
    retriever = ToolRetriever(persist_directory, default_k=k)
    return retriever.get_relevant_tools(query, k)

# Example usage and testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python retriever.py 'your query here'")
        sys.exit(1)

    query = sys.argv[1]
    print(f"Searching for tools relevant to: '{query}'")

    try:
        retriever = ToolRetriever()
        info = retriever.get_database_info()
        print(f"Database info: {info}")

        explanation = retriever.explain_retrieval(query)
        print(f"Retrieval explanation: {explanation}")

    except Exception as e:
        print(f"Error: {e}")
        print("Make sure you have run the ingestion pipeline first!")