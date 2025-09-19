"""
MetaMCP Integration Example: RAG-Based Tool Retrieval

This module demonstrates how to integrate the RAG-based tool retriever
into the existing metaMCP framework, replacing static tool loading
with dynamic, context-aware tool selection.

Based on analysis of: apps/backend/src/lib/metamcp/metamcp-proxy.ts
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

# Assume these would be the actual metaMCP imports
# from metamcp_proxy import createServer, mcpServerPool
# from client import ConnectedClient

# Our RAG components
from retriever import MetaMCPToolRetriever
from tool_definitions import ToolStandardizer

logger = logging.getLogger(__name__)

class RAGEnabledMetaMCPProxy:
    """
    Enhanced metaMCP proxy with RAG-based tool retrieval

    This class shows how to modify the existing metaMCP proxy to use
    dynamic tool retrieval instead of loading all tools statically.
    """

    def __init__(self, persist_directory: str = "./chroma_db",
                 collection_name: str = "metamcp_tools"):
        """
        Initialize the RAG-enabled proxy

        Args:
            persist_directory: Path to ChromaDB database
            collection_name: ChromaDB collection name
        """
        self.tool_retriever = MetaMCPToolRetriever(persist_directory, collection_name)
        self.tool_to_client_mapping = {}
        self.tool_to_server_uuid_mapping = {}
        self.fallback_tools = []

        # Track original metaMCP state for compatibility
        self.namespace_uuid = None
        self.session_id = None

        logger.info("Initialized RAG-enabled metaMCP proxy")

    def set_fallback_tools(self, core_tools: List[Dict[str, Any]]) -> None:
        """
        Set core tools that should always be available

        Args:
            core_tools: List of essential tool definitions
        """
        # Convert core tools to LangChain format
        standardizer = ToolStandardizer()
        for tool_data in core_tools:
            standardizer.add_mcp_tool(tool_data, "Core")

        self.fallback_tools = standardizer.get_langchain_tools()
        self.tool_retriever.set_fallback_tools(self.fallback_tools)

        logger.info(f"Set {len(self.fallback_tools)} fallback tools")

    async def discover_and_index_tools(self, namespace_uuid: str, session_id: str,
                                     include_inactive_servers: bool = False) -> None:
        """
        Discover tools from all MCP servers and index them for retrieval

        This replaces the tool discovery logic in the original metaMCP proxy.

        Args:
            namespace_uuid: MetaMCP namespace identifier
            session_id: Session identifier
            include_inactive_servers: Whether to include inactive servers
        """
        self.namespace_uuid = namespace_uuid
        self.session_id = session_id

        logger.info(f"Discovering tools for namespace {namespace_uuid}, session {session_id}")

        # This would be the actual metaMCP server discovery logic
        # For demonstration, we'll simulate it
        all_tools = await self._simulate_tool_discovery()

        # Register tools with the retriever
        self.tool_retriever.register_metamcp_tools(all_tools, self.tool_to_client_mapping)

        logger.info(f"Indexed {len(all_tools)} tools for RAG retrieval")

    async def _simulate_tool_discovery(self) -> List[Dict[str, Any]]:
        """
        Simulate the tool discovery process from metaMCP

        In the actual implementation, this would call the real metaMCP
        server discovery and tool enumeration logic.
        """
        # Simulated tools that would come from actual MCP servers
        simulated_tools = [
            {
                "name": "filesystem__read_file",
                "description": "Read the contents of a file from the filesystem",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to the file"},
                        "encoding": {"type": "string", "description": "File encoding"}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "git__status",
                "description": "Get the current status of a git repository",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "repo_path": {"type": "string", "description": "Path to repository"}
                    }
                }
            },
            {
                "name": "browser__navigate",
                "description": "Navigate to a URL in an automated browser",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to navigate to"},
                        "wait": {"type": "boolean", "description": "Wait for page load"}
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "email__send",
                "description": "Send an email message to recipients",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "description": "Recipient email"},
                        "subject": {"type": "string", "description": "Email subject"},
                        "body": {"type": "string", "description": "Email body"}
                    },
                    "required": ["to", "subject", "body"]
                }
            }
        ]

        # Simulate server connections
        for tool in simulated_tools:
            # In real implementation, this would be actual ConnectedClient objects
            mock_client = f"MockClient_{tool['name'].split('__')[0]}"
            self.tool_to_client_mapping[tool['name']] = mock_client
            self.tool_to_server_uuid_mapping[tool['name']] = f"server-uuid-{tool['name'].split('__')[0]}"

        return simulated_tools

    async def handle_list_tools_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle list tools request with RAG-based filtering

        This is the key modification - instead of returning all tools,
        we use the user's context to return only relevant tools.

        Args:
            request: The list tools request

        Returns:
            Filtered list of relevant tools
        """
        # Extract context from the request (this would depend on metaMCP's protocol)
        user_context = self._extract_user_context(request)

        if user_context:
            # Use RAG to get relevant tools
            relevant_tools = self.tool_retriever.get_relevant_tools(
                user_context,
                k=request.get('max_tools', 10)  # Configurable max tools
            )
            logger.info(f"Retrieved {len(relevant_tools)} relevant tools for context: '{user_context[:50]}...'")
        else:
            # No context available, use fallback tools
            relevant_tools = self.fallback_tools
            logger.info("No user context available, using fallback tools")

        # Convert back to metaMCP format
        tool_list = []
        for tool in relevant_tools:
            # Get the original tool schema and server info
            server_client = self.tool_to_client_mapping.get(tool.name)
            if server_client:
                tool_dict = {
                    "name": tool.name,
                    "description": tool.description,
                    # Add other required metaMCP tool fields
                }
                tool_list.append(tool_dict)

        return {
            "tools": tool_list,
            "nextCursor": None,  # For pagination if needed
            "_meta": {
                "rag_enabled": True,
                "total_available_tools": len(self.tool_retriever.get_all_available_tools()),
                "retrieved_tools": len(tool_list),
                "fallback_used": not bool(user_context)
            }
        }

    def _extract_user_context(self, request: Dict[str, Any]) -> Optional[str]:
        """
        Extract user context from the request for RAG retrieval

        This could come from:
        - Recent conversation history
        - Current task description
        - User's explicit request
        - Session metadata

        Args:
            request: The incoming request

        Returns:
            User context string or None
        """
        # Example context extraction strategies
        context_sources = [
            request.get('_meta', {}).get('user_query'),
            request.get('_meta', {}).get('task_description'),
            request.get('_meta', {}).get('recent_conversation'),
        ]

        for context in context_sources:
            if context and isinstance(context, str) and len(context.strip()) > 0:
                return context.strip()

        return None

    async def handle_call_tool_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle tool execution request

        Args:
            request: The call tool request

        Returns:
            Tool execution result
        """
        tool_name = request.get('params', {}).get('name')
        if not tool_name:
            return {"error": "No tool name provided"}

        # Get the server client for this tool
        server_client = self.tool_to_client_mapping.get(tool_name)
        if not server_client:
            return {"error": f"Tool {tool_name} not found or not available"}

        # In the actual implementation, this would forward the request
        # to the appropriate MCP server via the client connection
        logger.info(f"Executing tool {tool_name} via {server_client}")

        # Simulate tool execution
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Executed {tool_name} successfully (simulated)"
                }
            ],
            "_meta": {
                "rag_retrieved": True,
                "server_client": str(server_client)
            }
        }

class MetaMCPIntegrationHelper:
    """
    Helper class for integrating RAG retrieval into existing metaMCP code

    This shows the specific changes needed in the metaMCP proxy files.
    """

    @staticmethod
    def modify_create_server_function():
        """
        Example of how to modify the createServer function in metamcp-proxy.ts

        This shows the TypeScript-like logic that would need to be changed.
        """
        modification_example = '''
        // BEFORE (in metamcp-proxy.ts around line 144-199):
        const allServerTools: any[] = [];
        // ... paginated tool loading ...
        allTools.push(...toolsWithSource);

        // AFTER (with RAG integration):
        const ragProxy = new RAGEnabledMetaMCPProxy();
        await ragProxy.discover_and_index_tools(namespaceUuid, sessionId);

        // Replace the tools/list handler
        server.setRequestHandler(ListToolsRequestSchema, async (request) => {
            return await ragProxy.handle_list_tools_request(request);
        });

        // Keep the existing call tool handler but add RAG context
        server.setRequestHandler(CallToolRequestSchema, async (request) => {
            return await ragProxy.handle_call_tool_request(request);
        });
        '''

        return modification_example

    @staticmethod
    def create_middleware_for_context_extraction():
        """
        Example middleware to extract user context for RAG retrieval
        """
        middleware_example = '''
        // New middleware: extract-context.functional.ts
        export const createContextExtractionMiddleware = (
            conversationHistory: string[],
            currentTask?: string
        ): ListToolsHandler => {
            return (context: MetaMCPHandlerContext) => {
                return async (request) => {
                    // Add user context to request metadata
                    const userContext = currentTask ||
                                       conversationHistory.slice(-3).join(" ") ||
                                       "general task execution";

                    request.params = {
                        ...request.params,
                        _meta: {
                            ...request.params._meta,
                            user_query: userContext,
                            timestamp: Date.now()
                        }
                    };

                    return context.next(request);
                };
            };
        };
        '''

        return middleware_example

def create_requirements_file():
    """Generate requirements.txt for the RAG system"""
    requirements = '''# RAG-based Tool Retriever for MetaMCP
langchain>=0.1.0
chromadb>=0.4.0
sentence-transformers>=2.2.0
huggingface-hub>=0.16.0
numpy>=1.24.0
pydantic>=2.0.0

# Optional: For better embeddings
torch>=2.0.0

# Development dependencies
pytest>=7.0.0
black>=23.0.0
isort>=5.0.0
'''
    return requirements

# Example usage demonstration
async def demonstrate_integration():
    """Demonstrate how the RAG system would work in practice"""
    print("=== MetaMCP RAG Integration Demonstration ===")

    # Initialize the RAG-enabled proxy
    proxy = RAGEnabledMetaMCPProxy()

    # Set up fallback tools (essential tools always available)
    core_tools = [
        {
            "name": "read_file",
            "description": "Read a file from the filesystem",
            "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}}
        },
        {
            "name": "list_directory",
            "description": "List contents of a directory",
            "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}}
        }
    ]
    proxy.set_fallback_tools(core_tools)

    # Simulate tool discovery and indexing
    await proxy.discover_and_index_tools("test-namespace", "test-session")

    # Simulate different user requests
    test_requests = [
        {
            "method": "tools/list",
            "params": {
                "_meta": {
                    "user_query": "I need to check the git status and commit my changes"
                }
            }
        },
        {
            "method": "tools/list",
            "params": {
                "_meta": {
                    "user_query": "I want to automate some web browsing tasks"
                }
            }
        },
        {
            "method": "tools/list",
            "params": {}  # No context - should use fallback
        }
    ]

    # Process each request
    for i, request in enumerate(test_requests, 1):
        print(f"\n--- Test Request {i} ---")
        user_query = request.get("params", {}).get("_meta", {}).get("user_query", "No context")
        print(f"User Query: {user_query}")

        response = await proxy.handle_list_tools_request(request)
        print(f"Retrieved {len(response['tools'])} tools:")

        for tool in response['tools']:
            print(f"  - {tool['name']}: {tool['description'][:60]}...")

        print(f"Meta: {response.get('_meta', {})}")

if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(demonstrate_integration())

    # Show integration examples
    helper = MetaMCPIntegrationHelper()
    print("\n=== Integration Code Examples ===")
    print("\n1. Server Function Modification:")
    print(helper.modify_create_server_function())
    print("\n2. Context Extraction Middleware:")
    print(helper.create_middleware_for_context_extraction())

    # Generate requirements
    print("\n=== Requirements File ===")
    print(create_requirements_file())