#!/usr/bin/env python3
"""
Extract Real MCP Tool Definitions from Live Servers

This script connects to live MCP servers and extracts their actual tool definitions
using the MCP SDK, providing accurate data for the RAG system.
"""

import asyncio
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPServerConnector:
    """Connect to MCP servers and extract tool definitions"""

    def __init__(self, config_path: str = "/home/cordlesssteve/.config/claude-code/mcp.json"):
        self.config_path = config_path
        self.mcp_config = self._load_mcp_config()
        self.extracted_tools = []

    def _load_mcp_config(self) -> Dict[str, Any]:
        """Load MCP configuration from Claude Code"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            return config.get('mcpServers', {})
        except Exception as e:
            logger.error(f"Failed to load MCP config: {e}")
            return {}

    async def extract_tools_from_server(self, server_name: str, server_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract tools from a single MCP server"""
        logger.info(f"Extracting tools from {server_name}...")

        try:
            # Handle different server types
            if "url" in server_config:
                # HTTP server (like metamcp-essential)
                return await self._extract_from_http_server(server_name, server_config)
            elif "command" in server_config:
                # Command-based server (Node.js, Python, NPX)
                return await self._extract_from_command_server(server_name, server_config)
            else:
                logger.warning(f"Unknown server configuration for {server_name}")
                return []

        except Exception as e:
            logger.error(f"Failed to extract tools from {server_name}: {e}")
            return []

    async def _extract_from_http_server(self, server_name: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract tools from HTTP-based MCP server"""
        # For now, skip HTTP servers as they require special handling
        logger.info(f"Skipping HTTP server {server_name} (requires special handling)")
        return []

    async def _extract_from_command_server(self, server_name: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract tools from command-based MCP server"""
        command = config["command"]
        args = config.get("args", [])
        env = config.get("env", {})
        cwd = config.get("cwd")

        # Create a simple MCP client script to get tools
        client_script = self._create_mcp_client_script()

        # Build the full command
        full_command = [command] + args

        try:
            # Run the server and extract tools
            logger.info(f"Running: {' '.join(full_command)} in {cwd or 'current dir'}")

            # Create a process to run the MCP server
            process = await asyncio.create_subprocess_exec(
                *full_command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**env, "PATH": "/usr/bin:/usr/local/bin:/home/cordlesssteve/.local/bin"},
                cwd=cwd
            )

            # Send listTools request
            list_tools_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }

            request_json = json.dumps(list_tools_request) + "\n"

            # Send request and get response
            stdout, stderr = await asyncio.wait_for(
                process.communicate(request_json.encode()),
                timeout=10.0
            )

            if stderr:
                logger.warning(f"Server {server_name} stderr: {stderr.decode()}")

            # Parse response
            response_text = stdout.decode().strip()
            if response_text:
                try:
                    response = json.loads(response_text)
                    if "result" in response and "tools" in response["result"]:
                        tools = response["result"]["tools"]
                        logger.info(f"Found {len(tools)} tools in {server_name}")

                        # Add server metadata to each tool
                        for tool in tools:
                            tool["server"] = server_name
                            tool["server_config"] = {
                                "command": command,
                                "type": self._detect_server_type(command)
                            }

                        return tools
                    else:
                        logger.warning(f"No tools found in response from {server_name}")
                        return []
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse response from {server_name}: {e}")
                    logger.debug(f"Response text: {response_text}")
                    return []
            else:
                logger.warning(f"No response from {server_name}")
                return []

        except asyncio.TimeoutError:
            logger.error(f"Timeout connecting to {server_name}")
            if process:
                process.kill()
            return []
        except Exception as e:
            logger.error(f"Error connecting to {server_name}: {e}")
            return []

    def _detect_server_type(self, command: str) -> str:
        """Detect the type of server based on command"""
        if command == "node":
            return "nodejs"
        elif command == "python" or command == "uv":
            return "python"
        elif command == "npx":
            return "npm_package"
        elif command.endswith(".sh"):
            return "shell_script"
        else:
            return "unknown"

    def _create_mcp_client_script(self) -> str:
        """Create a simple MCP client script for testing"""
        script_content = '''
import asyncio
import json
import sys

async def test_mcp_server():
    # Read from stdin, write to stdout
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    }

    print(json.dumps(request))
    sys.stdout.flush()

    # Wait for response
    response = input()
    return response

if __name__ == "__main__":
    asyncio.run(test_mcp_server())
'''
        return script_content

    async def extract_all_tools(self) -> List[Dict[str, Any]]:
        """Extract tools from all configured MCP servers"""
        logger.info(f"Found {len(self.mcp_config)} MCP servers in configuration")

        all_tools = []
        successful_servers = []
        failed_servers = []

        for server_name, server_config in self.mcp_config.items():
            logger.info(f"\n{'='*50}")
            logger.info(f"Processing server: {server_name}")
            logger.info(f"Configuration: {server_config}")

            try:
                tools = await self.extract_tools_from_server(server_name, server_config)
                if tools:
                    all_tools.extend(tools)
                    successful_servers.append(server_name)
                    logger.info(f"✅ Successfully extracted {len(tools)} tools from {server_name}")
                else:
                    failed_servers.append(server_name)
                    logger.warning(f"❌ No tools extracted from {server_name}")
            except Exception as e:
                failed_servers.append(server_name)
                logger.error(f"❌ Failed to process {server_name}: {e}")

        logger.info(f"\n{'='*50}")
        logger.info(f"EXTRACTION SUMMARY")
        logger.info(f"{'='*50}")
        logger.info(f"Total tools extracted: {len(all_tools)}")
        logger.info(f"Successful servers ({len(successful_servers)}): {successful_servers}")
        logger.info(f"Failed servers ({len(failed_servers)}): {failed_servers}")

        return all_tools

    def save_tools(self, tools: List[Dict[str, Any]], filename: str = "real_mcp_tools.json"):
        """Save extracted tools to JSON file"""
        output_path = Path(filename)

        with open(output_path, 'w') as f:
            json.dump(tools, f, indent=2)

        logger.info(f"💾 Saved {len(tools)} real tools to {output_path}")

        # Create summary
        servers = {}
        for tool in tools:
            server = tool.get('server', 'unknown')
            if server not in servers:
                servers[server] = []
            servers[server].append(tool['name'])

        logger.info(f"\n📊 TOOL BREAKDOWN BY SERVER:")
        for server, tool_names in servers.items():
            logger.info(f"  {server}: {len(tool_names)} tools")
            for tool_name in tool_names[:3]:  # Show first 3
                logger.info(f"    - {tool_name}")
            if len(tool_names) > 3:
                logger.info(f"    ... and {len(tool_names) - 3} more")

async def main():
    """Main extraction process"""
    print("🚀 Starting Live MCP Tool Extraction")
    print("="*60)

    connector = MCPServerConnector()

    # Extract tools from all servers
    all_tools = await connector.extract_all_tools()

    if all_tools:
        # Save to file
        connector.save_tools(all_tools)

        print(f"\n🎉 Successfully extracted {len(all_tools)} real tools!")
        print(f"📁 Saved to: real_mcp_tools.json")
        print(f"🔄 Ready to update RAG system with real data!")
    else:
        print(f"\n❌ No tools extracted. Check server configurations.")

    return all_tools

if __name__ == "__main__":
    asyncio.run(main())