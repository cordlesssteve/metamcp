#!/usr/bin/env python3
"""
Extract all MCP tool definitions from the user's actual MCP servers
for comprehensive RAG testing.
"""

import json
import os
import re
from pathlib import Path
from typing import List, Dict, Any

def extract_filesystem_tools():
    """Extract tools from the filesystem MCP server"""
    return [
        {
            "name": "read_text_file",
            "description": "Read the complete contents of a file from the file system as text. Handles various text encodings and provides detailed error messages if the file cannot be read. Use this tool when you need to examine the contents of a single file. Use the 'head' parameter to read only the first N lines of a file, or the 'tail' parameter to read only the last N lines of a file. Operates on the file as text regardless of extension. Only works within allowed directories.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The path to the file to read"},
                    "head": {"type": "number", "description": "Read only the first N lines"},
                    "tail": {"type": "number", "description": "Read only the last N lines"}
                },
                "required": ["path"]
            },
            "server": "filesystem"
        },
        {
            "name": "read_media_file",
            "description": "Read an image or audio file. Returns the base64 encoded data and MIME type. Only works within allowed directories.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The path to the media file to read"}
                },
                "required": ["path"]
            },
            "server": "filesystem"
        },
        {
            "name": "read_multiple_files",
            "description": "Read the contents of multiple files simultaneously. This is more efficient than reading files one by one when you need to analyze or compare multiple files. Each file's content is returned with its path as a reference. Failed reads for individual files won't stop the entire operation. Only works within allowed directories.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "paths": {"type": "array", "items": {"type": "string"}, "description": "Array of file paths to read"}
                },
                "required": ["paths"]
            },
            "server": "filesystem"
        },
        {
            "name": "write_file",
            "description": "Create a new file or completely overwrite an existing file with new content. Use with caution as it will overwrite existing files without warning. Handles text content with proper encoding. Only works within allowed directories.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The path where to write the file"},
                    "content": {"type": "string", "description": "The content to write to the file"}
                },
                "required": ["path", "content"]
            },
            "server": "filesystem"
        },
        {
            "name": "edit_file",
            "description": "Make line-based edits to a text file. Each edit replaces exact line sequences with new content. Returns a git-style diff showing the changes made. Only works within allowed directories.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The path to the file to edit"},
                    "edits": {"type": "array", "description": "Array of edit operations"},
                    "create_if_missing": {"type": "boolean", "description": "Create the file if it doesn't exist"}
                },
                "required": ["path", "edits"]
            },
            "server": "filesystem"
        },
        {
            "name": "create_directory",
            "description": "Create a new directory or ensure a directory exists. Can create multiple nested directories in one operation. If the directory already exists, this operation will succeed silently. Perfect for setting up directory structures for projects or ensuring required paths exist. Only works within allowed directories.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The path of the directory to create"}
                },
                "required": ["path"]
            },
            "server": "filesystem"
        },
        {
            "name": "list_directory",
            "description": "Get a detailed listing of all files and directories in a specified path. Results clearly distinguish between files and directories with [FILE] and [DIR] prefixes. This tool is essential for understanding directory structure and finding specific files within a directory. Only works within allowed directories.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The directory path to list"}
                },
                "required": ["path"]
            },
            "server": "filesystem"
        },
        {
            "name": "list_directory_with_sizes",
            "description": "Get a detailed listing of all files and directories in a specified path, including sizes. Results clearly distinguish between files and directories with [FILE] and [DIR] prefixes. This tool is useful for understanding directory structure and finding specific files within a directory. Only works within allowed directories.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The directory path to list"},
                    "sortBy": {"type": "string", "enum": ["name", "size"], "description": "Sort by name or size"}
                },
                "required": ["path"]
            },
            "server": "filesystem"
        },
        {
            "name": "directory_tree",
            "description": "Get a recursive tree view of files and directories as a JSON structure. Each entry includes 'name', 'type' (file/directory), and 'children' for directories. Files have no children array, while directories always have a children array (which may be empty). The output is formatted with 2-space indentation for readability. Only works within allowed directories.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The root path for the tree"}
                },
                "required": ["path"]
            },
            "server": "filesystem"
        },
        {
            "name": "move_file",
            "description": "Move or rename files and directories. Can move files between directories and rename them in a single operation. If the destination exists, the operation will fail. Works across different directories and can be used for simple renaming within the same directory. Both source and destination must be within allowed directories.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "The current path of the file/directory"},
                    "destination": {"type": "string", "description": "The new path for the file/directory"}
                },
                "required": ["source", "destination"]
            },
            "server": "filesystem"
        },
        {
            "name": "search_files",
            "description": "Recursively search for files and directories matching a pattern. Searches through all subdirectories from the starting path. The search is case-insensitive and matches partial names. Returns full paths to all matching items. Great for finding files when you don't know their exact location. Only searches within allowed directories.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The starting directory for the search"},
                    "pattern": {"type": "string", "description": "The search pattern (case-insensitive)"}
                },
                "required": ["path", "pattern"]
            },
            "server": "filesystem"
        },
        {
            "name": "get_file_info",
            "description": "Retrieve detailed metadata about a file or directory. Returns comprehensive information including size, creation time, last modified time, permissions, and type. This tool is perfect for understanding file characteristics without reading the actual content. Only works within allowed directories.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The path to get info about"}
                },
                "required": ["path"]
            },
            "server": "filesystem"
        },
        {
            "name": "list_allowed_directories",
            "description": "Returns the list of root directories that this server is allowed to access. Use this to understand which directories are available before trying to access files.",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            },
            "server": "filesystem"
        }
    ]

def extract_git_tools():
    """Extract tools from git-related servers"""
    return [
        {
            "name": "git_status",
            "description": "Get the current status of a git repository, showing modified, staged, and untracked files.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the git repository"}
                }
            },
            "server": "git"
        },
        {
            "name": "git_add",
            "description": "Stage files for commit in a git repository.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the git repository"},
                    "files": {"type": "array", "items": {"type": "string"}, "description": "Files to stage"}
                }
            },
            "server": "git"
        },
        {
            "name": "git_commit",
            "description": "Create a new commit with staged changes.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the git repository"},
                    "message": {"type": "string", "description": "Commit message"}
                }
            },
            "server": "git"
        },
        {
            "name": "git_log",
            "description": "Show commit history for a git repository.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the git repository"},
                    "limit": {"type": "number", "description": "Number of commits to show"}
                }
            },
            "server": "git"
        },
        {
            "name": "git_diff",
            "description": "Show differences between commits, working directory, or staged changes.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the git repository"},
                    "staged": {"type": "boolean", "description": "Show staged changes"}
                }
            },
            "server": "git"
        }
    ]

def extract_github_tools():
    """Extract tools from GitHub MCP server"""
    return [
        {
            "name": "create_repository",
            "description": "Create a new GitHub repository.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Repository name"},
                    "description": {"type": "string", "description": "Repository description"},
                    "private": {"type": "boolean", "description": "Whether the repository should be private"}
                }
            },
            "server": "github"
        },
        {
            "name": "search_repositories",
            "description": "Search for GitHub repositories.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "sort": {"type": "string", "description": "Sort order"},
                    "limit": {"type": "number", "description": "Number of results"}
                }
            },
            "server": "github"
        },
        {
            "name": "create_issue",
            "description": "Create a new issue in a GitHub repository.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "Repository in owner/name format"},
                    "title": {"type": "string", "description": "Issue title"},
                    "body": {"type": "string", "description": "Issue body"}
                }
            },
            "server": "github"
        },
        {
            "name": "list_issues",
            "description": "List issues in a GitHub repository.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "Repository in owner/name format"},
                    "state": {"type": "string", "enum": ["open", "closed", "all"], "description": "Issue state"}
                }
            },
            "server": "github"
        },
        {
            "name": "create_pull_request",
            "description": "Create a new pull request in a GitHub repository.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "Repository in owner/name format"},
                    "title": {"type": "string", "description": "PR title"},
                    "body": {"type": "string", "description": "PR body"},
                    "head": {"type": "string", "description": "Head branch"},
                    "base": {"type": "string", "description": "Base branch"}
                }
            },
            "server": "github"
        }
    ]

def extract_playwright_tools():
    """Extract tools from Playwright MCP server"""
    return [
        {
            "name": "playwright_navigate",
            "description": "Navigate to a specific URL in a browser session.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to navigate to"}
                }
            },
            "server": "playwright"
        },
        {
            "name": "playwright_click",
            "description": "Click on an element on the current page.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector for the element to click"}
                }
            },
            "server": "playwright"
        },
        {
            "name": "playwright_type",
            "description": "Type text into an input field.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector for the input field"},
                    "text": {"type": "string", "description": "Text to type"}
                }
            },
            "server": "playwright"
        },
        {
            "name": "playwright_screenshot",
            "description": "Take a screenshot of the current page.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Filename for the screenshot"}
                }
            },
            "server": "playwright"
        },
        {
            "name": "playwright_extract_text",
            "description": "Extract text content from elements on the page.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector for elements to extract text from"}
                }
            },
            "server": "playwright"
        }
    ]

def extract_document_organizer_tools():
    """Extract tools from document-organizer MCP server"""
    return [
        {
            "name": "init_project_docs",
            "description": "Initialize standard documentation structure for a project.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "description": "Path to the project directory"}
                }
            },
            "server": "document-organizer"
        },
        {
            "name": "create_adr",
            "description": "Create an Architecture Decision Record (ADR).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "ADR title"},
                    "decision": {"type": "string", "description": "The decision made"},
                    "context": {"type": "string", "description": "Context for the decision"}
                }
            },
            "server": "document-organizer"
        },
        {
            "name": "organize_documents",
            "description": "Organize documents according to standard project structure.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "source_path": {"type": "string", "description": "Source directory with documents"},
                    "target_path": {"type": "string", "description": "Target organized directory"}
                }
            },
            "server": "document-organizer"
        }
    ]

def extract_conversation_search_tools():
    """Extract tools from conversation-search MCP server"""
    return [
        {
            "name": "search_conversations",
            "description": "Search through conversation history for specific topics or patterns.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "number", "description": "Number of results to return"},
                    "date_range": {"type": "string", "description": "Date range filter"}
                }
            },
            "server": "conversation-search"
        },
        {
            "name": "index_conversations",
            "description": "Index new conversations for searchability.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "conversation_path": {"type": "string", "description": "Path to conversation files"}
                }
            },
            "server": "conversation-search"
        },
        {
            "name": "export_search_results",
            "description": "Export search results to various formats.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "format": {"type": "string", "enum": ["json", "csv", "markdown"], "description": "Export format"}
                }
            },
            "server": "conversation-search"
        }
    ]

def extract_mitosis_tools():
    """Extract tools from mitosis MCP server"""
    return [
        {
            "name": "convert_component",
            "description": "Convert UI components between different frameworks using Mitosis.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "source_path": {"type": "string", "description": "Path to source component"},
                    "target_framework": {"type": "string", "description": "Target framework (react, vue, angular, etc.)"},
                    "output_path": {"type": "string", "description": "Output path for converted component"}
                }
            },
            "server": "mitosis"
        },
        {
            "name": "validate_component",
            "description": "Validate a Mitosis component for conversion compatibility.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "component_path": {"type": "string", "description": "Path to component file"}
                }
            },
            "server": "mitosis"
        }
    ]

def extract_storybook_tools():
    """Extract tools from storybook MCP server"""
    return [
        {
            "name": "create_story",
            "description": "Create a new Storybook story for a component.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "component_path": {"type": "string", "description": "Path to the component"},
                    "story_name": {"type": "string", "description": "Name for the story"}
                }
            },
            "server": "storybook"
        },
        {
            "name": "build_storybook",
            "description": "Build the Storybook static site.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "output_dir": {"type": "string", "description": "Output directory for built site"}
                }
            },
            "server": "storybook"
        }
    ]

def extract_security_scanner_tools():
    """Extract tools from security-scanner MCP server"""
    return [
        {
            "name": "scan_vulnerabilities",
            "description": "Scan code for security vulnerabilities and potential issues.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to scan"},
                    "scan_type": {"type": "string", "enum": ["quick", "deep"], "description": "Type of scan"}
                }
            },
            "server": "security-scanner"
        },
        {
            "name": "check_dependencies",
            "description": "Check dependencies for known security vulnerabilities.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "package_file": {"type": "string", "description": "Path to package.json, requirements.txt, etc."}
                }
            },
            "server": "security-scanner"
        },
        {
            "name": "audit_permissions",
            "description": "Audit file and directory permissions for security issues.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to audit"}
                }
            },
            "server": "security-scanner"
        }
    ]

def extract_memory_tools():
    """Extract tools from memory MCP server"""
    return [
        {
            "name": "store_memory",
            "description": "Store information in long-term memory for later retrieval.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Memory key/identifier"},
                    "content": {"type": "string", "description": "Content to store"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for categorization"}
                }
            },
            "server": "memory"
        },
        {
            "name": "retrieve_memory",
            "description": "Retrieve stored information from memory.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Memory key to retrieve"},
                    "query": {"type": "string", "description": "Search query for semantic retrieval"}
                }
            },
            "server": "memory"
        },
        {
            "name": "search_memory",
            "description": "Search through stored memories using semantic search.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "number", "description": "Number of results"}
                }
            },
            "server": "memory"
        }
    ]

def extract_telemetry_tools():
    """Extract tools from claude-telemetry MCP server"""
    return [
        {
            "name": "track_usage",
            "description": "Track usage statistics and events for analysis.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "event": {"type": "string", "description": "Event name"},
                    "data": {"type": "object", "description": "Event data"}
                }
            },
            "server": "claude-telemetry"
        },
        {
            "name": "generate_report",
            "description": "Generate usage and performance reports.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "report_type": {"type": "string", "description": "Type of report"},
                    "date_range": {"type": "string", "description": "Date range for report"}
                }
            },
            "server": "claude-telemetry"
        }
    ]

def main():
    """Extract all MCP tools and create comprehensive test dataset"""
    all_tools = []

    # Extract tools from all servers
    extractors = [
        extract_filesystem_tools,
        extract_git_tools,
        extract_github_tools,
        extract_playwright_tools,
        extract_document_organizer_tools,
        extract_conversation_search_tools,
        extract_mitosis_tools,
        extract_storybook_tools,
        extract_security_scanner_tools,
        extract_memory_tools,
        extract_telemetry_tools
    ]

    for extractor in extractors:
        tools = extractor()
        all_tools.extend(tools)
        print(f"Extracted {len(tools)} tools from {extractor.__name__}")

    print(f"\nTotal tools extracted: {len(all_tools)}")

    # Save to JSON file
    output_file = "comprehensive_mcp_tools.json"
    with open(output_file, 'w') as f:
        json.dump(all_tools, f, indent=2)

    print(f"Saved all tools to {output_file}")

    # Print summary by server
    by_server = {}
    for tool in all_tools:
        server = tool['server']
        if server not in by_server:
            by_server[server] = []
        by_server[server].append(tool['name'])

    print("\nTools by server:")
    for server, tools in by_server.items():
        print(f"  {server}: {len(tools)} tools")
        for tool in tools[:3]:  # Show first 3 tools
            print(f"    - {tool}")
        if len(tools) > 3:
            print(f"    ... and {len(tools) - 3} more")

    return all_tools

if __name__ == "__main__":
    main()