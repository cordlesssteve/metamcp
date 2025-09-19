#!/usr/bin/env python3
"""
Simple MCP Tool Extractor

Extract tools from live MCP servers using direct process communication.
"""

import asyncio
import json
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleMCPExtractor:
    """Simple MCP tool extractor using subprocess communication"""

    def __init__(self):
        self.config_path = "/home/cordlesssteve/.config/claude-code/mcp.json"
        self.extracted_tools = []

    def load_mcp_config(self) -> Dict[str, Any]:
        """Load MCP server configuration"""
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        return config.get('mcpServers', {})

    async def test_single_server(self, server_name: str, server_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Test a single MCP server to extract its tools"""
        logger.info(f"Testing {server_name}...")

        if "url" in server_config:
            logger.info(f"  Skipping HTTP server {server_name}")
            return []

        command = server_config.get("command")
        args = server_config.get("args", [])
        env = server_config.get("env", {})
        cwd = server_config.get("cwd")

        if not command:
            logger.warning(f"  No command found for {server_name}")
            return []

        # Handle missing tools
        if command == "uv" and not self._command_exists("uv"):
            # Try with python3 instead for uv commands
            if args and args[0] == "run" and len(args) >= 3:
                command = "python3"
                args = ["-m"] + args[2:]  # Convert "uv run -m module" to "python3 -m module"
            else:
                logger.warning(f"  uv not available for {server_name}")
                return []
        elif command == "python" and not self._command_exists("python"):
            command = "python3"  # Use python3 instead of python

        try:
            # Build environment with proper PATH including nvm node
            full_env = {
                "PATH": "/home/cordlesssteve/.nvm/versions/node/v20.19.3/bin:/home/cordlesssteve/.local/bin:/usr/bin:/usr/local/bin",
                "NODE_PATH": "/home/cordlesssteve/.nvm/versions/node/v20.19.3/lib/node_modules",
                **env
            }

            # Start the MCP server process
            full_command = [command] + args
            logger.info(f"  Running: {' '.join(full_command)}")

            process = await asyncio.create_subprocess_exec(
                *full_command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=full_env,
                cwd=cwd
            )

            # MCP initialize request
            initialize_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "clientInfo": {
                        "name": "mcp-tool-extractor",
                        "version": "1.0.0"
                    }
                }
            }

            # Send initialize
            init_message = json.dumps(initialize_request) + "\n"
            process.stdin.write(init_message.encode())
            await process.stdin.drain()

            # Wait a bit for initialization
            await asyncio.sleep(0.5)

            # Send tools/list request
            list_tools_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }

            list_message = json.dumps(list_tools_request) + "\n"
            process.stdin.write(list_message.encode())
            await process.stdin.drain()

            # Close stdin to signal we're done
            process.stdin.close()

            # Read response with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=5.0
                )

                if stderr:
                    stderr_text = stderr.decode()
                    if "error" not in stderr_text.lower():
                        logger.debug(f"  {server_name} stderr: {stderr_text[:200]}...")

                # Parse stdout for JSON responses
                stdout_text = stdout.decode()
                tools = self._parse_mcp_responses(stdout_text, server_name)

                # Add server metadata
                for tool in tools:
                    tool["server"] = server_name
                    tool["server_type"] = self._detect_server_type(command)

                if tools:
                    logger.info(f"  ✅ Found {len(tools)} tools in {server_name}")
                    return tools
                else:
                    logger.warning(f"  ❌ No tools found in {server_name}")
                    return []

            except asyncio.TimeoutError:
                logger.error(f"  ⏰ Timeout for {server_name}")
                process.kill()
                return []

        except Exception as e:
            logger.error(f"  ❌ Error with {server_name}: {e}")
            return []

    def _parse_mcp_responses(self, stdout_text: str, server_name: str) -> List[Dict[str, Any]]:
        """Parse MCP JSON-RPC responses from stdout"""
        tools = []

        # Split by lines and look for JSON responses
        lines = stdout_text.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            try:
                response = json.loads(line)

                # Check if this is a tools/list response
                if (isinstance(response, dict) and
                    "result" in response and
                    isinstance(response["result"], dict) and
                    "tools" in response["result"]):

                    tools.extend(response["result"]["tools"])

            except json.JSONDecodeError:
                # Skip non-JSON lines
                continue

        return tools

    def _command_exists(self, command: str) -> bool:
        """Check if a command exists in the system"""
        import shutil
        return shutil.which(command) is not None

    def _detect_server_type(self, command: str) -> str:
        """Detect server type from command"""
        if command == "node":
            return "nodejs"
        elif command in ["python", "python3", "uv"]:
            return "python"
        elif command == "npx":
            return "npm_package"
        elif command.endswith(".sh"):
            return "shell_script"
        else:
            return "unknown"

    async def extract_all_tools(self) -> List[Dict[str, Any]]:
        """Extract tools from all servers"""
        logger.info("🔧 Loading MCP server configuration...")

        config = self.load_mcp_config()
        logger.info(f"📋 Found {len(config)} servers: {list(config.keys())}")

        all_tools = []
        successful_servers = []
        failed_servers = []

        for server_name, server_config in config.items():
            try:
                tools = await self.test_single_server(server_name, server_config)
                if tools:
                    all_tools.extend(tools)
                    successful_servers.append(server_name)
                else:
                    failed_servers.append(server_name)
            except Exception as e:
                logger.error(f"Failed to process {server_name}: {e}")
                failed_servers.append(server_name)

        logger.info(f"\n📊 EXTRACTION RESULTS:")
        logger.info(f"  ✅ Successful: {len(successful_servers)} servers")
        logger.info(f"  ❌ Failed: {len(failed_servers)} servers")
        logger.info(f"  🛠️  Total tools: {len(all_tools)}")

        if successful_servers:
            logger.info(f"  Success: {', '.join(successful_servers)}")
        if failed_servers:
            logger.info(f"  Failed: {', '.join(failed_servers)}")

        return all_tools

    def save_tools(self, tools: List[Dict[str, Any]], filename: str = "real_mcp_tools.json"):
        """Save extracted tools"""
        with open(filename, 'w') as f:
            json.dump(tools, f, indent=2)

        logger.info(f"💾 Saved {len(tools)} tools to {filename}")

        # Show breakdown
        by_server = {}
        for tool in tools:
            server = tool.get('server', 'unknown')
            if server not in by_server:
                by_server[server] = []
            by_server[server].append(tool['name'])

        logger.info(f"\n📋 Tools by server:")
        for server, tool_names in by_server.items():
            logger.info(f"  {server}: {tool_names}")

async def main():
    """Main function"""
    print("🚀 Simple MCP Tool Extractor")
    print("="*50)

    extractor = SimpleMCPExtractor()
    tools = await extractor.extract_all_tools()

    if tools:
        extractor.save_tools(tools)
        print(f"\n🎉 Success! Extracted {len(tools)} real tools")
    else:
        print(f"\n❌ No tools extracted")

    return tools

if __name__ == "__main__":
    asyncio.run(main())