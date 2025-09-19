"""
Tool Definition Standardization Module for MetaMCP RAG System

This module provides utilities to standardize MCP tools into LangChain Tool objects
with rich, semantic descriptions for optimal vector embedding and retrieval.
"""

from langchain.tools import Tool
from typing import List, Dict, Any, Callable
import json
import logging

logger = logging.getLogger(__name__)

class StandardizedTool:
    """Wrapper for standardized tool with enhanced metadata"""

    def __init__(self, name: str, func: Callable, description: str,
                 original_schema: Dict[str, Any] = None, server_source: str = None):
        self.name = name
        self.func = func
        self.description = description
        self.original_schema = original_schema or {}
        self.server_source = server_source

    def to_langchain_tool(self) -> Tool:
        """Convert to LangChain Tool object"""
        return Tool(
            name=self.name,
            func=self.func,
            description=self.description
        )

class ToolStandardizer:
    """Converts MCP tools to standardized LangChain tools with enhanced descriptions"""

    def __init__(self):
        self.tools: List[StandardizedTool] = []

    def add_mcp_tool(self, tool_data: Dict[str, Any], server_name: str = "unknown") -> StandardizedTool:
        """
        Convert an MCP tool definition to a standardized tool

        Args:
            tool_data: MCP tool definition dict with 'name', 'description', 'inputSchema'
            server_name: Name of the source MCP server

        Returns:
            StandardizedTool object
        """
        name = tool_data.get('name', 'unnamed_tool')
        base_description = tool_data.get('description', 'No description provided')
        input_schema = tool_data.get('inputSchema', {})

        # Enhance description for better semantic retrieval
        enhanced_description = self._enhance_description(
            name, base_description, input_schema, server_name
        )

        # Create a callable function wrapper
        def tool_executor(*args, **kwargs):
            """Placeholder executor - will be replaced by actual MCP call in integration"""
            return f"Tool {name} executed with args: {args}, kwargs: {kwargs}"

        standardized_tool = StandardizedTool(
            name=name,
            func=tool_executor,
            description=enhanced_description,
            original_schema=tool_data,
            server_source=server_name
        )

        self.tools.append(standardized_tool)
        return standardized_tool

    def _enhance_description(self, name: str, description: str,
                           input_schema: Dict[str, Any], server_name: str) -> str:
        """
        Create a rich, semantic description for vector embedding

        This enhanced description includes:
        - Original description
        - Tool purpose and use cases
        - Input parameters and types
        - Source server context
        - Keywords for better retrieval
        """
        enhanced_parts = [
            f"Tool: {name}",
            f"Source: {server_name} MCP server",
            f"Description: {description}",
        ]

        # Add parameter information
        if input_schema and 'properties' in input_schema:
            params = input_schema['properties']
            param_descriptions = []

            for param_name, param_def in params.items():
                param_type = param_def.get('type', 'unknown')
                param_desc = param_def.get('description', 'No description')
                param_descriptions.append(f"- {param_name} ({param_type}): {param_desc}")

            if param_descriptions:
                enhanced_parts.append("Parameters:")
                enhanced_parts.extend(param_descriptions)

        # Add use case keywords based on tool name and description
        keywords = self._extract_keywords(name, description)
        if keywords:
            enhanced_parts.append(f"Keywords: {', '.join(keywords)}")

        # Add context about when to use this tool
        use_cases = self._infer_use_cases(name, description)
        if use_cases:
            enhanced_parts.append(f"Use when: {use_cases}")

        return "\n".join(enhanced_parts)

    def _extract_keywords(self, name: str, description: str) -> List[str]:
        """Extract relevant keywords for semantic search"""
        keywords = set()

        # Extract from tool name
        name_parts = name.lower().replace('_', ' ').replace('-', ' ').split()
        keywords.update(name_parts)

        # Extract key action words from description
        action_words = [
            'create', 'read', 'write', 'update', 'delete', 'get', 'set', 'list',
            'search', 'find', 'execute', 'run', 'send', 'receive', 'fetch',
            'upload', 'download', 'generate', 'analyze', 'process', 'transform'
        ]

        description_lower = description.lower()
        for word in action_words:
            if word in description_lower:
                keywords.add(word)

        # Extract domain-specific keywords
        domain_keywords = {
            'file': ['filesystem', 'directory', 'folder', 'document'],
            'git': ['version control', 'repository', 'commit', 'branch'],
            'database': ['data', 'query', 'record', 'table'],
            'api': ['web', 'http', 'request', 'endpoint'],
            'browser': ['web', 'automation', 'selenium', 'playwright'],
            'email': ['message', 'communication', 'send'],
            'auth': ['authentication', 'login', 'security', 'token']
        }

        for domain, related_words in domain_keywords.items():
            if domain in description_lower or domain in name.lower():
                keywords.update(related_words)

        return list(keywords)

    def _infer_use_cases(self, name: str, description: str) -> str:
        """Infer when this tool should be used based on patterns"""
        name_lower = name.lower()
        desc_lower = description.lower()

        use_cases = []

        # File operations
        if any(word in name_lower for word in ['file', 'read', 'write', 'directory']):
            use_cases.append("working with files or directories")

        # Git operations
        if any(word in name_lower for word in ['git', 'commit', 'branch', 'repo']):
            use_cases.append("managing version control or repositories")

        # Web/API operations
        if any(word in name_lower for word in ['web', 'http', 'api', 'request']):
            use_cases.append("making web requests or API calls")

        # Browser automation
        if any(word in name_lower for word in ['browser', 'click', 'navigate']):
            use_cases.append("automating browser interactions")

        # Data operations
        if any(word in name_lower for word in ['search', 'query', 'find', 'filter']):
            use_cases.append("searching or querying data")

        # Communication
        if any(word in name_lower for word in ['send', 'email', 'message', 'notify']):
            use_cases.append("sending messages or notifications")

        return "; ".join(use_cases) if use_cases else "general purpose tasks"

    def get_langchain_tools(self) -> List[Tool]:
        """Get all tools as LangChain Tool objects"""
        return [tool.to_langchain_tool() for tool in self.tools]

    def get_tool_descriptions(self) -> List[str]:
        """Get all enhanced descriptions for embedding"""
        return [tool.description for tool in self.tools]

    def get_tool_metadata(self) -> List[Dict[str, Any]]:
        """Get metadata for each tool (for ChromaDB storage)"""
        return [
            {
                "name": tool.name,
                "server_source": tool.server_source,
                "original_schema": json.dumps(tool.original_schema)
            }
            for tool in self.tools
        ]

    def load_from_metamcp_format(self, metamcp_tools: List[Dict[str, Any]]) -> None:
        """
        Load tools from metaMCP format (as seen in the proxy code)

        Args:
            metamcp_tools: List of tool definitions from metaMCP
        """
        for tool_data in metamcp_tools:
            # Extract server name from the prefixed tool name
            tool_name = tool_data.get('name', '')
            if '__' in tool_name:
                server_name = tool_name.split('__')[0].replace('_', ' ').title()
                actual_tool_name = tool_name.split('__', 1)[1]
            else:
                server_name = "Unknown Server"
                actual_tool_name = tool_name

            # Update tool data with clean name
            clean_tool_data = dict(tool_data)
            clean_tool_data['name'] = actual_tool_name

            self.add_mcp_tool(clean_tool_data, server_name)

# Example usage and sample tools for testing
def create_sample_tools() -> List[StandardizedTool]:
    """Create sample tools for testing the system"""
    standardizer = ToolStandardizer()

    sample_tools = [
        {
            "name": "read_file",
            "description": "Read the contents of a file from the filesystem",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to read"},
                    "encoding": {"type": "string", "description": "File encoding, defaults to utf-8"}
                },
                "required": ["path"]
            }
        },
        {
            "name": "git_status",
            "description": "Get the current status of a git repository",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "repository_path": {"type": "string", "description": "Path to git repository"}
                }
            }
        },
        {
            "name": "web_search",
            "description": "Search the web for information using a search engine",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query terms"},
                    "max_results": {"type": "integer", "description": "Maximum number of results"}
                },
                "required": ["query"]
            }
        },
        {
            "name": "send_email",
            "description": "Send an email message to recipients",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject line"},
                    "body": {"type": "string", "description": "Email body content"}
                },
                "required": ["to", "subject", "body"]
            }
        },
        {
            "name": "browser_navigate",
            "description": "Navigate to a URL in an automated browser",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to navigate to"},
                    "wait_for_load": {"type": "boolean", "description": "Wait for page to fully load"}
                },
                "required": ["url"]
            }
        }
    ]

    for i, tool_data in enumerate(sample_tools):
        server_name = f"Sample Server {i+1}"
        standardizer.add_mcp_tool(tool_data, server_name)

    return standardizer.tools

if __name__ == "__main__":
    # Test the standardization
    tools = create_sample_tools()
    print(f"Created {len(tools)} standardized tools:")
    for tool in tools:
        print(f"\n--- {tool.name} ---")
        print(tool.description)