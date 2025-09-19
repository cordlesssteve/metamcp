#!/usr/bin/env python3
"""
Complete Test Suite for MetaMCP RAG Tool Retriever

This script tests the entire pipeline from tool ingestion to retrieval,
demonstrating the context window savings and retrieval accuracy.
"""

import asyncio
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import List, Dict, Any

# Test imports
from tool_definitions import ToolStandardizer, create_sample_tools
from ingest import ToolIngestionPipeline
from retriever import ToolRetriever, MetaMCPToolRetriever
from integration_example import RAGEnabledMetaMCPProxy

def create_comprehensive_test_tools() -> List[Dict[str, Any]]:
    """Create a comprehensive set of test tools for evaluation"""
    return [
        # File system tools
        {
            "name": "filesystem__read_file",
            "description": "Read the complete contents of a file from the local filesystem. Supports various encodings and provides detailed error messages if the file cannot be read.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute path to the file to read"},
                    "encoding": {"type": "string", "description": "File encoding, defaults to utf-8"},
                    "max_size": {"type": "integer", "description": "Maximum file size to read in bytes"}
                },
                "required": ["path"]
            }
        },
        {
            "name": "filesystem__write_file",
            "description": "Write content to a file on the local filesystem. Creates directories if needed and handles various encodings.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path where to write the file"},
                    "content": {"type": "string", "description": "Content to write to the file"},
                    "encoding": {"type": "string", "description": "File encoding, defaults to utf-8"},
                    "create_dirs": {"type": "boolean", "description": "Create parent directories if they don't exist"}
                },
                "required": ["path", "content"]
            }
        },
        {
            "name": "filesystem__list_directory",
            "description": "List all files and directories in a specified path. Provides detailed file information including sizes and permissions.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path to list"},
                    "recursive": {"type": "boolean", "description": "List subdirectories recursively"},
                    "include_hidden": {"type": "boolean", "description": "Include hidden files and directories"}
                },
                "required": ["path"]
            }
        },

        # Git tools
        {
            "name": "git__status",
            "description": "Get the current working tree status of a git repository, showing modified, staged, and untracked files.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Path to the git repository"},
                    "porcelain": {"type": "boolean", "description": "Use porcelain format for machine parsing"}
                }
            }
        },
        {
            "name": "git__commit",
            "description": "Create a new commit in the git repository with staged changes and a descriptive message.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Path to the git repository"},
                    "message": {"type": "string", "description": "Commit message"},
                    "add_all": {"type": "boolean", "description": "Stage all changes before committing"}
                },
                "required": ["message"]
            }
        },
        {
            "name": "git__branch",
            "description": "List, create, or delete branches in a git repository. Supports both local and remote branch operations.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Path to the git repository"},
                    "action": {"type": "string", "enum": ["list", "create", "delete"], "description": "Branch operation to perform"},
                    "branch_name": {"type": "string", "description": "Name of the branch for create/delete operations"}
                },
                "required": ["action"]
            }
        },

        # Web browsing tools
        {
            "name": "browser__navigate",
            "description": "Navigate to a specific URL in an automated browser session. Supports waiting for page load and handling redirects.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to navigate to"},
                    "wait_for_load": {"type": "boolean", "description": "Wait for page to fully load"},
                    "timeout": {"type": "integer", "description": "Maximum time to wait in seconds"}
                },
                "required": ["url"]
            }
        },
        {
            "name": "browser__click_element",
            "description": "Click on a web page element identified by CSS selector, XPath, or text content. Supports various click types.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector, XPath, or text to identify the element"},
                    "selector_type": {"type": "string", "enum": ["css", "xpath", "text"], "description": "Type of selector"},
                    "click_type": {"type": "string", "enum": ["left", "right", "double"], "description": "Type of click"}
                },
                "required": ["selector"]
            }
        },
        {
            "name": "browser__extract_text",
            "description": "Extract text content from web page elements or the entire page. Supports CSS selectors and XPath.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector or XPath to target specific elements"},
                    "all_matches": {"type": "boolean", "description": "Extract from all matching elements"},
                    "include_html": {"type": "boolean", "description": "Include HTML markup in the result"}
                }
            }
        },

        # Email tools
        {
            "name": "email__send",
            "description": "Send an email message to one or more recipients with optional attachments and formatting.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "to": {"type": "array", "items": {"type": "string"}, "description": "Recipient email addresses"},
                    "subject": {"type": "string", "description": "Email subject line"},
                    "body": {"type": "string", "description": "Email body content"},
                    "cc": {"type": "array", "items": {"type": "string"}, "description": "CC recipient email addresses"},
                    "bcc": {"type": "array", "items": {"type": "string"}, "description": "BCC recipient email addresses"},
                    "attachments": {"type": "array", "items": {"type": "string"}, "description": "File paths for attachments"}
                },
                "required": ["to", "subject", "body"]
            }
        },
        {
            "name": "email__read_inbox",
            "description": "Read and retrieve emails from an inbox with filtering and search capabilities.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "folder": {"type": "string", "description": "Email folder to read from", "default": "INBOX"},
                    "limit": {"type": "integer", "description": "Maximum number of emails to retrieve"},
                    "unread_only": {"type": "boolean", "description": "Only retrieve unread emails"},
                    "search_query": {"type": "string", "description": "Search query to filter emails"}
                }
            }
        },

        # Database tools
        {
            "name": "database__query",
            "description": "Execute SQL queries against a database connection with support for parameterized queries and result formatting.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "connection_string": {"type": "string", "description": "Database connection string"},
                    "query": {"type": "string", "description": "SQL query to execute"},
                    "parameters": {"type": "object", "description": "Query parameters for prepared statements"},
                    "format": {"type": "string", "enum": ["json", "csv", "table"], "description": "Result format"}
                },
                "required": ["connection_string", "query"]
            }
        },
        {
            "name": "database__backup",
            "description": "Create a backup of a database with compression and scheduling options.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "connection_string": {"type": "string", "description": "Database connection string"},
                    "backup_path": {"type": "string", "description": "Path where to store the backup"},
                    "compress": {"type": "boolean", "description": "Compress the backup file"},
                    "tables": {"type": "array", "items": {"type": "string"}, "description": "Specific tables to backup"}
                },
                "required": ["connection_string", "backup_path"]
            }
        },

        # API tools
        {
            "name": "api__http_request",
            "description": "Make HTTP requests to web APIs with support for all common methods, headers, authentication, and data formats.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "API endpoint URL"},
                    "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"], "description": "HTTP method"},
                    "headers": {"type": "object", "description": "HTTP headers"},
                    "data": {"type": "object", "description": "Request body data"},
                    "auth": {"type": "object", "description": "Authentication credentials"},
                    "timeout": {"type": "integer", "description": "Request timeout in seconds"}
                },
                "required": ["url"]
            }
        },
        {
            "name": "api__graphql_query",
            "description": "Execute GraphQL queries and mutations against GraphQL endpoints with variable support.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "endpoint": {"type": "string", "description": "GraphQL endpoint URL"},
                    "query": {"type": "string", "description": "GraphQL query or mutation"},
                    "variables": {"type": "object", "description": "Query variables"},
                    "headers": {"type": "object", "description": "HTTP headers for authentication"}
                },
                "required": ["endpoint", "query"]
            }
        },

        # System tools
        {
            "name": "system__execute_command",
            "description": "Execute system commands and shell scripts with output capture and error handling.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command to execute"},
                    "working_directory": {"type": "string", "description": "Working directory for command execution"},
                    "environment": {"type": "object", "description": "Environment variables"},
                    "timeout": {"type": "integer", "description": "Command timeout in seconds"},
                    "capture_output": {"type": "boolean", "description": "Capture stdout and stderr"}
                },
                "required": ["command"]
            }
        },
        {
            "name": "system__monitor_resources",
            "description": "Monitor system resources including CPU, memory, disk usage, and network statistics.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "duration": {"type": "integer", "description": "Monitoring duration in seconds"},
                    "interval": {"type": "integer", "description": "Sampling interval in seconds"},
                    "resources": {"type": "array", "items": {"type": "string"}, "description": "Specific resources to monitor"}
                }
            }
        }
    ]

class RAGSystemTester:
    """Comprehensive tester for the RAG tool retrieval system"""

    def __init__(self):
        self.temp_dir = None
        self.test_results = {}

    def setup_test_environment(self):
        """Set up temporary directory for testing"""
        self.temp_dir = tempfile.mkdtemp(prefix="metamcp_rag_test_")
        print(f"Created test environment: {self.temp_dir}")

    def cleanup_test_environment(self):
        """Clean up test environment"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            print(f"Cleaned up test environment: {self.temp_dir}")

    def test_tool_standardization(self) -> Dict[str, Any]:
        """Test tool standardization and description enhancement"""
        print("\n=== Testing Tool Standardization ===")

        standardizer = ToolStandardizer()
        test_tools = create_comprehensive_test_tools()

        start_time = time.time()
        for tool_data in test_tools:
            standardizer.add_mcp_tool(tool_data, "Test Server")
        standardization_time = time.time() - start_time

        # Test description enhancement
        sample_tool = standardizer.tools[0]
        original_desc_len = len(test_tools[0]['description'])
        enhanced_desc_len = len(sample_tool.description)

        results = {
            "tools_processed": len(standardizer.tools),
            "processing_time": standardization_time,
            "original_description_length": original_desc_len,
            "enhanced_description_length": enhanced_desc_len,
            "enhancement_ratio": enhanced_desc_len / original_desc_len,
            "keywords_extracted": len(standardizer._extract_keywords(
                sample_tool.name, test_tools[0]['description']
            ))
        }

        print(f"Processed {results['tools_processed']} tools in {results['processing_time']:.3f}s")
        print(f"Description enhancement ratio: {results['enhancement_ratio']:.2f}x")
        print(f"Keywords extracted: {results['keywords_extracted']}")

        return results

    def test_ingestion_pipeline(self) -> Dict[str, Any]:
        """Test the ingestion pipeline performance and accuracy"""
        print("\n=== Testing Ingestion Pipeline ===")

        persist_dir = os.path.join(self.temp_dir, "test_chroma_db")
        pipeline = ToolIngestionPipeline(persist_dir)

        # Create test data file
        test_tools = create_comprehensive_test_tools()
        test_file = os.path.join(self.temp_dir, "test_tools.json")
        with open(test_file, 'w') as f:
            json.dump(test_tools, f)

        # Test ingestion
        start_time = time.time()
        pipeline.load_tools_from_metamcp_json(test_file)
        loading_time = time.time() - start_time

        start_time = time.time()
        pipeline.create_vector_store()
        indexing_time = time.time() - start_time

        # Get statistics
        stats = pipeline.get_database_stats()

        results = {
            "loading_time": loading_time,
            "indexing_time": indexing_time,
            "total_time": loading_time + indexing_time,
            "database_stats": stats,
            "database_size_mb": self._get_directory_size(persist_dir) / (1024 * 1024)
        }

        print(f"Loading time: {results['loading_time']:.3f}s")
        print(f"Indexing time: {results['indexing_time']:.3f}s")
        print(f"Database size: {results['database_size_mb']:.2f} MB")
        print(f"Tools indexed: {stats.get('total_tools', 'unknown')}")

        return results

    def test_retrieval_accuracy(self) -> Dict[str, Any]:
        """Test retrieval accuracy with various queries"""
        print("\n=== Testing Retrieval Accuracy ===")

        persist_dir = os.path.join(self.temp_dir, "test_chroma_db")
        retriever = ToolRetriever(persist_dir, default_k=5)

        # Register the actual tool objects with the retriever
        from tool_definitions import ToolStandardizer
        standardizer = ToolStandardizer()
        test_tools = create_comprehensive_test_tools()  # Get the tools data
        standardizer.load_from_metamcp_format(test_tools)
        langchain_tools = standardizer.get_langchain_tools()
        retriever.register_tools(langchain_tools)

        # Test queries with expected tools
        test_queries = [
            {
                "query": "I need to read files and check git status",
                "expected_tools": ["filesystem__read_file", "git__status"],
                "category": "development"
            },
            {
                "query": "Browse the web and click on elements",
                "expected_tools": ["browser__navigate", "browser__click_element"],
                "category": "web_automation"
            },
            {
                "query": "Send emails and manage my inbox",
                "expected_tools": ["email__send", "email__read_inbox"],
                "category": "communication"
            },
            {
                "query": "Query database and backup data",
                "expected_tools": ["database__query", "database__backup"],
                "category": "data_management"
            },
            {
                "query": "Make API calls and HTTP requests",
                "expected_tools": ["api__http_request", "api__graphql_query"],
                "category": "api_integration"
            }
        ]

        accuracy_results = []
        retrieval_times = []

        for test_case in test_queries:
            start_time = time.time()
            retrieved_tools = retriever.get_relevant_tools(test_case["query"], k=5)
            retrieval_time = time.time() - start_time
            retrieval_times.append(retrieval_time)

            retrieved_names = [tool.name for tool in retrieved_tools]
            expected_names = test_case["expected_tools"]

            # Calculate accuracy metrics
            true_positives = len(set(retrieved_names) & set(expected_names))
            precision = true_positives / len(retrieved_names) if retrieved_names else 0
            recall = true_positives / len(expected_names) if expected_names else 0
            f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

            accuracy_results.append({
                "query": test_case["query"],
                "category": test_case["category"],
                "retrieved_tools": retrieved_names,
                "expected_tools": expected_names,
                "precision": precision,
                "recall": recall,
                "f1_score": f1_score,
                "retrieval_time": retrieval_time
            })

            print(f"Query: {test_case['query'][:50]}...")
            print(f"  Retrieved: {retrieved_names}")
            print(f"  Expected: {expected_names}")
            print(f"  F1 Score: {f1_score:.3f}, Time: {retrieval_time:.3f}s")

        # Calculate overall metrics
        avg_precision = sum(r["precision"] for r in accuracy_results) / len(accuracy_results)
        avg_recall = sum(r["recall"] for r in accuracy_results) / len(accuracy_results)
        avg_f1 = sum(r["f1_score"] for r in accuracy_results) / len(accuracy_results)
        avg_retrieval_time = sum(retrieval_times) / len(retrieval_times)

        results = {
            "test_cases": accuracy_results,
            "overall_metrics": {
                "average_precision": avg_precision,
                "average_recall": avg_recall,
                "average_f1_score": avg_f1,
                "average_retrieval_time": avg_retrieval_time
            }
        }

        print(f"\nOverall Results:")
        print(f"  Average Precision: {avg_precision:.3f}")
        print(f"  Average Recall: {avg_recall:.3f}")
        print(f"  Average F1 Score: {avg_f1:.3f}")
        print(f"  Average Retrieval Time: {avg_retrieval_time:.3f}s")

        return results

    def test_context_window_savings(self) -> Dict[str, Any]:
        """Test and demonstrate context window savings"""
        print("\n=== Testing Context Window Savings ===")

        # Simulate token counting (rough approximation)
        def estimate_tokens(text: str) -> int:
            """Rough token estimation: ~4 characters per token"""
            return len(text) // 4

        # Calculate tokens for all tools (static loading)
        test_tools = create_comprehensive_test_tools()
        total_static_tokens = 0

        for tool in test_tools:
            tool_text = json.dumps(tool, indent=2)
            total_static_tokens += estimate_tokens(tool_text)

        # Calculate tokens for RAG-retrieved tools (various query scenarios)
        persist_dir = os.path.join(self.temp_dir, "test_chroma_db")
        retriever = ToolRetriever(persist_dir, default_k=5)

        # Register the actual tool objects with the retriever
        from tool_definitions import ToolStandardizer
        standardizer = ToolStandardizer()
        standardizer.load_from_metamcp_format(test_tools)
        langchain_tools = standardizer.get_langchain_tools()
        retriever.register_tools(langchain_tools)

        rag_scenarios = [
            "Need to work with files",
            "Web automation task",
            "Database operations",
            "API integration work",
            "System administration"
        ]

        rag_token_usage = []
        for scenario in rag_scenarios:
            retrieved_tools = retriever.get_relevant_tools(scenario, k=5)
            scenario_tokens = 0

            for tool in retrieved_tools:
                # Estimate tokens for minimal tool representation
                tool_text = f"Tool: {tool.name}\nDescription: {tool.description}"
                scenario_tokens += estimate_tokens(tool_text)

            rag_token_usage.append(scenario_tokens)

        avg_rag_tokens = sum(rag_token_usage) / len(rag_token_usage)
        token_savings = total_static_tokens - avg_rag_tokens
        savings_percentage = (token_savings / total_static_tokens) * 100

        results = {
            "static_loading_tokens": total_static_tokens,
            "average_rag_tokens": avg_rag_tokens,
            "token_savings": token_savings,
            "savings_percentage": savings_percentage,
            "rag_scenarios": list(zip(rag_scenarios, rag_token_usage))
        }

        print(f"Static loading tokens: {total_static_tokens:,}")
        print(f"Average RAG tokens: {avg_rag_tokens:.0f}")
        print(f"Token savings: {token_savings:.0f} ({savings_percentage:.1f}%)")

        return results

    async def test_integration_demo(self) -> Dict[str, Any]:
        """Test the complete integration with metaMCP simulation"""
        print("\n=== Testing MetaMCP Integration ===")

        persist_dir = os.path.join(self.temp_dir, "test_chroma_db")
        proxy = RAGEnabledMetaMCPProxy(persist_dir)

        # Simulate the complete workflow
        start_time = time.time()
        await proxy.discover_and_index_tools("test-namespace", "test-session")
        setup_time = time.time() - start_time

        # Test various request scenarios
        test_requests = [
            {
                "scenario": "File operations",
                "request": {
                    "method": "tools/list",
                    "params": {
                        "_meta": {
                            "user_query": "I need to read and write files, also list directories"
                        }
                    }
                }
            },
            {
                "scenario": "Git workflow",
                "request": {
                    "method": "tools/list",
                    "params": {
                        "_meta": {
                            "user_query": "Check git status and make a commit"
                        }
                    }
                }
            },
            {
                "scenario": "No context",
                "request": {
                    "method": "tools/list",
                    "params": {}
                }
            }
        ]

        integration_results = []
        for test_case in test_requests:
            start_time = time.time()
            response = await proxy.handle_list_tools_request(test_case["request"])
            response_time = time.time() - start_time

            integration_results.append({
                "scenario": test_case["scenario"],
                "tools_returned": len(response["tools"]),
                "response_time": response_time,
                "metadata": response.get("_meta", {})
            })

            print(f"Scenario: {test_case['scenario']}")
            print(f"  Tools returned: {len(response['tools'])}")
            print(f"  Response time: {response_time:.3f}s")
            print(f"  Fallback used: {response.get('_meta', {}).get('fallback_used', False)}")

        results = {
            "setup_time": setup_time,
            "integration_tests": integration_results
        }

        return results

    def _get_directory_size(self, directory: str) -> int:
        """Get total size of directory in bytes"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                total_size += os.path.getsize(filepath)
        return total_size

    def generate_test_report(self) -> str:
        """Generate a comprehensive test report"""
        report = f"""
# MetaMCP RAG Tool Retriever Test Report

Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}

## Test Environment
- Temporary directory: {self.temp_dir}
- Python version: {os.sys.version}

## Summary of Results

"""

        for test_name, results in self.test_results.items():
            report += f"### {test_name.replace('_', ' ').title()}\n"

            if isinstance(results, dict):
                for key, value in results.items():
                    if isinstance(value, (int, float)):
                        report += f"- {key.replace('_', ' ').title()}: {value:.3f}\n"
                    else:
                        report += f"- {key.replace('_', ' ').title()}: {value}\n"
            else:
                report += f"- Result: {results}\n"

            report += "\n"

        return report

    async def run_all_tests(self):
        """Run the complete test suite"""
        print("Starting MetaMCP RAG Tool Retriever Test Suite")
        print("=" * 60)

        try:
            self.setup_test_environment()

            # Run all tests
            self.test_results["tool_standardization"] = self.test_tool_standardization()
            self.test_results["ingestion_pipeline"] = self.test_ingestion_pipeline()
            self.test_results["retrieval_accuracy"] = self.test_retrieval_accuracy()
            self.test_results["context_window_savings"] = self.test_context_window_savings()
            self.test_results["integration_demo"] = await self.test_integration_demo()

            # Generate report
            report = self.generate_test_report()
            report_file = os.path.join(self.temp_dir, "test_report.md")
            with open(report_file, 'w') as f:
                f.write(report)

            print(f"\n{'=' * 60}")
            print("All tests completed successfully!")
            print(f"Test report saved to: {report_file}")
            print("=" * 60)

            return self.test_results

        finally:
            # Keep test environment for inspection
            print(f"Test environment preserved at: {self.temp_dir}")
            print("Run cleanup_test_environment() to remove it")

async def main():
    """Main test execution"""
    tester = RAGSystemTester()
    results = await tester.run_all_tests()

    print("\n=== Final Summary ===")
    context_savings = results.get("context_window_savings", {})
    if context_savings:
        savings_pct = context_savings.get("savings_percentage", 0)
        print(f"Context window savings: {savings_pct:.1f}%")

    accuracy = results.get("retrieval_accuracy", {})
    if accuracy and "overall_metrics" in accuracy:
        f1_score = accuracy["overall_metrics"].get("average_f1_score", 0)
        print(f"Average retrieval F1 score: {f1_score:.3f}")

    return results

if __name__ == "__main__":
    asyncio.run(main())