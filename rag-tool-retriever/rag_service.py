#!/usr/bin/env python3
"""
RAG Tool Selection HTTP Service

Lightweight HTTP service that provides tool selection based on semantic similarity.
Integrates with MetaMCP's TypeScript backend.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Import our RAG components
from retriever import ToolRetriever
from tool_definitions import ToolStandardizer


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ToolSelectionRequest(BaseModel):
    """Request model for tool selection"""
    query: str = Field(..., description="User intent or query description")
    available_tools: List[str] = Field(
        ...,
        description="List of available tool names to filter from"
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of tools to return"
    )
    similarity_threshold: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="Minimum similarity score threshold"
    )


class ToolSelectionResponse(BaseModel):
    """Response model for tool selection"""
    selected_tools: List[str] = Field(
        description="List of selected tool names in order of relevance"
    )
    scores: List[float] = Field(
        description="Similarity scores for each selected tool"
    )
    query: str = Field(description="Original query")
    total_available: int = Field(description="Total number of available tools")
    total_selected: int = Field(description="Number of tools selected")


class RAGService:
    """RAG tool selection service"""

    def __init__(self, vector_db_path: str = "./real_tools_db"):
        self.vector_db_path = Path(vector_db_path)
        self.retriever: Optional[ToolRetriever] = None
        self._initialize_retriever()

    def _initialize_retriever(self):
        """Initialize the RAG retriever"""
        try:
            if not self.vector_db_path.exists():
                logger.warning(f"Vector database not found at {self.vector_db_path}")
                logger.info("Attempting to create vector database from real tools...")
                self._create_vector_db()

            logger.info(f"Initializing RAG retriever from {self.vector_db_path}")
            self.retriever = ToolRetriever(str(self.vector_db_path))

            # Load and register tools from the tools file
            self._load_and_register_tools()

            logger.info("RAG retriever initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize RAG retriever: {e}")
            self.retriever = None

    def _load_and_register_tools(self):
        """Load tools from JSON file and register them with the retriever"""
        try:
            # Look for real tools JSON file
            tools_file = Path("real_mcp_tools.json")
            if not tools_file.exists():
                tools_file = Path("comprehensive_mcp_tools_real.json")

            if not tools_file.exists():
                logger.warning("No tools JSON file found for tool registration")
                return

            logger.info(f"Loading tools from {tools_file}")
            with open(tools_file, 'r') as f:
                tools_data = json.load(f)

            # Convert to LangChain tools and register
            standardizer = ToolStandardizer()
            tools = []
            for tool_data in tools_data:
                std_tool = standardizer.add_mcp_tool(tool_data, tool_data.get('server', 'unknown'))
                tools.append(std_tool.to_langchain_tool())

            self.retriever.register_tools(tools)
            logger.info(f"Registered {len(tools)} tools with retriever")

        except Exception as e:
            logger.error(f"Failed to load and register tools: {e}")
            # Continue without tools - service will still work but return empty results

    def _create_vector_db(self):
        """Create vector database if it doesn't exist"""
        try:
            from ingest import ToolIngestionPipeline

            # Look for real tools JSON file
            tools_file = Path("real_mcp_tools.json")
            if not tools_file.exists():
                tools_file = Path("comprehensive_mcp_tools_real.json")

            if not tools_file.exists():
                logger.error("No tools JSON file found for vector database creation")
                return

            logger.info(f"Creating vector database from {tools_file}")
            pipeline = ToolIngestionPipeline(persist_directory=str(self.vector_db_path))

            # Load and process tools
            with open(tools_file, 'r') as f:
                tools_data = json.load(f)

            standardizer = ToolStandardizer()
            tools = [standardizer.mcp_to_langchain_tool(tool) for tool in tools_data]

            pipeline.create_vector_store(tools)
            logger.info("Vector database created successfully")

        except Exception as e:
            logger.error(f"Failed to create vector database: {e}")
            raise

    def select_tools(
        self,
        query: str,
        available_tools: List[str],
        limit: int = 10,
        similarity_threshold: float = 0.0
    ) -> ToolSelectionResponse:
        """Select most relevant tools based on query"""

        if not self.retriever:
            logger.error("RAG retriever not initialized")
            raise HTTPException(
                status_code=503,
                detail="RAG service not available - retriever not initialized"
            )

        try:
            # Get tools with scores from RAG system
            tools_with_scores = self.retriever.get_tools_with_scores(
                query,
                k=min(limit * 2, 50)  # Get more initially for filtering
            )

            # Filter to only available tools and apply threshold
            selected_tools = []
            scores = []

            for tool, score in tools_with_scores:
                if tool.name in available_tools and score >= similarity_threshold:
                    selected_tools.append(tool.name)
                    scores.append(float(score))

                    if len(selected_tools) >= limit:
                        break

            logger.info(
                f"Query: '{query}' -> Selected {len(selected_tools)}/{len(available_tools)} tools"
            )

            return ToolSelectionResponse(
                selected_tools=selected_tools,
                scores=scores,
                query=query,
                total_available=len(available_tools),
                total_selected=len(selected_tools)
            )

        except Exception as e:
            logger.error(f"Error in tool selection: {e}")
            raise HTTPException(status_code=500, detail=f"Tool selection failed: {str(e)}")


# Initialize the service
rag_service = RAGService()

# Create FastAPI app
app = FastAPI(
    title="MetaMCP RAG Tool Selection Service",
    description="Semantic tool selection service for MetaMCP",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "retriever_available": rag_service.retriever is not None,
        "vector_db_path": str(rag_service.vector_db_path)
    }


@app.post("/select-tools", response_model=ToolSelectionResponse)
async def select_tools(request: ToolSelectionRequest):
    """Select most relevant tools based on user query"""
    return rag_service.select_tools(
        query=request.query,
        available_tools=request.available_tools,
        limit=request.limit,
        similarity_threshold=request.similarity_threshold
    )


@app.get("/stats")
async def get_stats():
    """Get service statistics"""
    if not rag_service.retriever:
        return {"error": "RAG service not available"}

    return {
        "tool_count": len(rag_service.retriever.tool_registry),
        "vector_db_path": str(rag_service.vector_db_path),
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2"  # fallback model
    }


if __name__ == "__main__":
    # Configuration from environment
    host = os.getenv("RAG_SERVICE_HOST", "127.0.0.1")
    port = int(os.getenv("RAG_SERVICE_PORT", "8002"))

    logger.info(f"Starting RAG service on {host}:{port}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )