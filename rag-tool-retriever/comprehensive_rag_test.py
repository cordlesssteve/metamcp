#!/usr/bin/env python3
"""
Comprehensive RAG Test with Real MCP Tools

This script tests the RAG system using all real MCP tools from the user's actual servers,
providing realistic scenarios and complex multi-tool queries.
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
from tool_definitions import ToolStandardizer
from ingest import ToolIngestionPipeline
from retriever import ToolRetriever
from integration_example import RAGEnabledMetaMCPProxy

class ComprehensiveRAGTester:
    """Test the RAG system with comprehensive real-world scenarios"""

    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="comprehensive_rag_test_")
        self.test_results = {}

    def load_comprehensive_tools(self) -> List[Dict[str, Any]]:
        """Load all real MCP tools"""
        with open("comprehensive_mcp_tools.json", 'r') as f:
            return json.load(f)

    def create_complex_test_scenarios(self) -> List[Dict[str, Any]]:
        """Create realistic, complex test scenarios that require multiple tools"""
        return [
            {
                "scenario": "Web scraping and data analysis",
                "query": "I need to navigate to a website, take a screenshot, extract text content, and save the results to a file for analysis",
                "expected_tools": ["playwright_navigate", "playwright_screenshot", "playwright_extract_text", "write_file"],
                "category": "web_automation_data"
            },
            {
                "scenario": "Code repository management",
                "query": "Check git status, review recent commits, create a GitHub issue about found problems, and document the findings",
                "expected_tools": ["git_status", "git_log", "create_issue", "write_file"],
                "category": "development_workflow"
            },
            {
                "scenario": "Project documentation setup",
                "query": "Initialize project documentation structure, create an architecture decision record, and organize existing documents",
                "expected_tools": ["init_project_docs", "create_adr", "organize_documents"],
                "category": "documentation"
            },
            {
                "scenario": "Security audit and reporting",
                "query": "Scan the codebase for vulnerabilities, check dependencies for security issues, audit file permissions, and generate a comprehensive security report",
                "expected_tools": ["scan_vulnerabilities", "check_dependencies", "audit_permissions", "write_file"],
                "category": "security"
            },
            {
                "scenario": "Component development workflow",
                "query": "Convert a React component to Vue using Mitosis, create a Storybook story for it, and document the conversion process",
                "expected_tools": ["convert_component", "create_story", "write_file"],
                "category": "frontend_development"
            },
            {
                "scenario": "Data exploration and search",
                "query": "Search through conversation history for specific topics, retrieve relevant memories, and export the findings to a markdown report",
                "expected_tools": ["search_conversations", "retrieve_memory", "export_search_results", "write_file"],
                "category": "knowledge_management"
            },
            {
                "scenario": "File system operations",
                "query": "Find all JavaScript files in a project, read their contents, analyze them for patterns, and create a summary report",
                "expected_tools": ["search_files", "read_multiple_files", "write_file"],
                "category": "file_analysis"
            },
            {
                "scenario": "Repository analysis and cleanup",
                "query": "List directory contents with sizes, get detailed file info for large files, and create a cleanup plan",
                "expected_tools": ["list_directory_with_sizes", "get_file_info", "write_file"],
                "category": "repository_maintenance"
            },
            {
                "scenario": "Development environment setup",
                "query": "Create project directories, initialize git repository, set up GitHub repo, and track the setup process",
                "expected_tools": ["create_directory", "git_status", "create_repository", "track_usage"],
                "category": "project_initialization"
            },
            {
                "scenario": "Cross-platform component migration",
                "query": "Validate a component for Mitosis conversion, convert it to multiple frameworks, and build Storybook documentation",
                "expected_tools": ["validate_component", "convert_component", "build_storybook"],
                "category": "component_tooling"
            },
            {
                "scenario": "Research and documentation",
                "query": "Search GitHub repositories for similar projects, read documentation files, store findings in memory, and create a research summary",
                "expected_tools": ["search_repositories", "read_text_file", "store_memory", "write_file"],
                "category": "research"
            },
            {
                "scenario": "Media processing workflow",
                "query": "Read image files from a directory, take screenshots of web pages, and organize media files for a project",
                "expected_tools": ["list_directory", "read_media_file", "playwright_screenshot", "move_file"],
                "category": "media_processing"
            }
        ]

    def test_ingestion_with_comprehensive_tools(self) -> Dict[str, Any]:
        """Test ingestion with all real MCP tools"""
        print("\n=== Testing Comprehensive Tool Ingestion ===")

        # Load comprehensive tools
        tools = self.load_comprehensive_tools()

        # Save to temporary file
        tools_file = os.path.join(self.temp_dir, "comprehensive_tools.json")
        with open(tools_file, 'w') as f:
            json.dump(tools, f, indent=2)

        # Test ingestion
        persist_dir = os.path.join(self.temp_dir, "comprehensive_chroma_db")

        start_time = time.time()
        pipeline = ToolIngestionPipeline(persist_dir)
        pipeline.load_tools_from_metamcp_json(tools_file)
        pipeline.create_vector_store()  # ← This was missing!
        ingestion_time = time.time() - start_time

        # Get database stats
        try:
            import chromadb
            client = chromadb.PersistentClient(path=persist_dir)
            collection = client.get_collection("metamcp_tools")
            doc_count = collection.count()
        except:
            doc_count = len(tools)

        results = {
            "tools_processed": len(tools),
            "ingestion_time": ingestion_time,
            "database_size_mb": self._get_directory_size(persist_dir) / (1024 * 1024),
            "documents_stored": doc_count,
            "servers_covered": len(set(tool.get('server', 'unknown') for tool in tools))
        }

        print(f"Processed {results['tools_processed']} tools from {results['servers_covered']} servers")
        print(f"Ingestion time: {results['ingestion_time']:.2f}s")
        print(f"Database size: {results['database_size_mb']:.2f} MB")
        print(f"Documents stored: {results['documents_stored']}")

        return results

    def test_complex_retrieval_scenarios(self) -> Dict[str, Any]:
        """Test retrieval with complex, realistic scenarios"""
        print("\n=== Testing Complex Retrieval Scenarios ===")

        persist_dir = os.path.join(self.temp_dir, "comprehensive_chroma_db")
        retriever = ToolRetriever(persist_dir, default_k=10)  # More tools per query

        # Register comprehensive tools
        tools = self.load_comprehensive_tools()
        standardizer = ToolStandardizer()
        standardizer.load_from_metamcp_format(tools)
        langchain_tools = standardizer.get_langchain_tools()
        retriever.register_tools(langchain_tools)

        # Test complex scenarios
        scenarios = self.create_complex_test_scenarios()
        results = []

        for scenario in scenarios:
            start_time = time.time()
            retrieved_tools = retriever.get_relevant_tools(scenario["query"], k=10)
            retrieval_time = time.time() - start_time

            retrieved_names = [tool.name for tool in retrieved_tools]
            expected_names = scenario["expected_tools"]

            # Calculate recall and precision
            retrieved_set = set(retrieved_names)
            expected_set = set(expected_names)

            intersection = retrieved_set.intersection(expected_set)
            precision = len(intersection) / len(retrieved_set) if retrieved_set else 0
            recall = len(intersection) / len(expected_set) if expected_set else 0
            f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

            result = {
                "scenario": scenario["scenario"],
                "category": scenario["category"],
                "query": scenario["query"],
                "retrieved": retrieved_names[:5],  # Top 5 tools
                "expected": expected_names,
                "precision": precision,
                "recall": recall,
                "f1_score": f1_score,
                "retrieval_time": retrieval_time,
                "tools_found": len(intersection)
            }
            results.append(result)

            print(f"\\nScenario: {scenario['scenario']}")
            print(f"  Retrieved: {retrieved_names[:5]}")
            print(f"  Expected: {expected_names}")
            print(f"  F1 Score: {f1_score:.3f}, Time: {retrieval_time:.3f}s")

        # Calculate overall metrics
        avg_precision = sum(r["precision"] for r in results) / len(results)
        avg_recall = sum(r["recall"] for r in results) / len(results)
        avg_f1 = sum(r["f1_score"] for r in results) / len(results)
        avg_time = sum(r["retrieval_time"] for r in results) / len(results)

        print(f"\\nOverall Results:")
        print(f"  Average Precision: {avg_precision:.3f}")
        print(f"  Average Recall: {avg_recall:.3f}")
        print(f"  Average F1 Score: {avg_f1:.3f}")
        print(f"  Average Retrieval Time: {avg_time:.3f}s")

        return {
            "scenarios": results,
            "overall_metrics": {
                "avg_precision": avg_precision,
                "avg_recall": avg_recall,
                "avg_f1_score": avg_f1,
                "avg_retrieval_time": avg_time
            }
        }

    def test_scalability_with_comprehensive_dataset(self) -> Dict[str, Any]:
        """Test how well the system scales with a large, realistic tool dataset"""
        print("\n=== Testing Scalability with Comprehensive Dataset ===")

        persist_dir = os.path.join(self.temp_dir, "comprehensive_chroma_db")
        retriever = ToolRetriever(persist_dir, default_k=5)

        # Register tools
        tools = self.load_comprehensive_tools()
        standardizer = ToolStandardizer()
        standardizer.load_from_metamcp_format(tools)
        langchain_tools = standardizer.get_langchain_tools()
        retriever.register_tools(langchain_tools)

        # Test various query complexities
        queries = [
            "simple file read",
            "create a new GitHub repository with documentation",
            "comprehensive security audit including vulnerability scanning, dependency checks, and permission auditing with detailed reporting",
            "full development workflow: git operations, code analysis, component conversion, testing, and documentation generation",
            "complex web automation: navigate multiple pages, extract data, process images, store results, and generate analytics reports"
        ]

        results = []
        for query in queries:
            times = []
            for _ in range(5):  # Run each query 5 times
                start_time = time.time()
                tools = retriever.get_relevant_tools(query, k=10)
                end_time = time.time()
                times.append(end_time - start_time)

            avg_time = sum(times) / len(times)
            results.append({
                "query": query[:50] + "..." if len(query) > 50 else query,
                "avg_time": avg_time,
                "tools_retrieved": len(tools)
            })
            print(f"Query: {query[:50]}... - Avg time: {avg_time:.3f}s")

        return {"scalability_results": results}

    def test_token_efficiency(self) -> Dict[str, Any]:
        """Test token efficiency with comprehensive tool set"""
        print("\n=== Testing Token Efficiency ===")

        tools = self.load_comprehensive_tools()

        # Calculate tokens for static loading (all tools)
        def estimate_tokens(text: str) -> int:
            return len(text) // 4

        total_static_tokens = 0
        for tool in tools:
            tool_text = json.dumps(tool, indent=2)
            total_static_tokens += estimate_tokens(tool_text)

        # Test RAG efficiency with various scenarios
        persist_dir = os.path.join(self.temp_dir, "comprehensive_chroma_db")
        retriever = ToolRetriever(persist_dir, default_k=5)

        standardizer = ToolStandardizer()
        standardizer.load_from_metamcp_format(tools)
        langchain_tools = standardizer.get_langchain_tools()
        retriever.register_tools(langchain_tools)

        scenarios = [
            "Read and write files",
            "Git operations and GitHub integration",
            "Web automation with Playwright",
            "Security scanning and reporting",
            "Component development and testing"
        ]

        rag_token_usage = []
        for scenario in scenarios:
            retrieved_tools = retriever.get_relevant_tools(scenario, k=5)
            scenario_tokens = 0

            for tool in retrieved_tools:
                tool_text = f"Tool: {tool.name}\\nDescription: {tool.description}"
                scenario_tokens += estimate_tokens(tool_text)

            rag_token_usage.append(scenario_tokens)

        avg_rag_tokens = sum(rag_token_usage) / len(rag_token_usage)
        token_savings = total_static_tokens - avg_rag_tokens
        savings_percentage = (token_savings / total_static_tokens) * 100

        print(f"Static loading tokens: {total_static_tokens:,}")
        print(f"Average RAG tokens: {avg_rag_tokens:,.0f}")
        print(f"Token savings: {token_savings:,.0f} ({savings_percentage:.1f}%)")

        return {
            "static_tokens": total_static_tokens,
            "avg_rag_tokens": avg_rag_tokens,
            "token_savings": token_savings,
            "savings_percentage": savings_percentage
        }

    def test_multi_server_scenarios(self) -> Dict[str, Any]:
        """Test scenarios that span multiple MCP servers"""
        print("\n=== Testing Multi-Server Scenarios ===")

        persist_dir = os.path.join(self.temp_dir, "comprehensive_chroma_db")
        retriever = ToolRetriever(persist_dir, default_k=8)

        tools = self.load_comprehensive_tools()
        standardizer = ToolStandardizer()
        standardizer.load_from_metamcp_format(tools)
        langchain_tools = standardizer.get_langchain_tools()
        retriever.register_tools(langchain_tools)

        multi_server_scenarios = [
            {
                "query": "Complete development workflow: check git status, scan for security issues, create GitHub issue, document in memory",
                "expected_servers": ["git", "security-scanner", "github", "memory"]
            },
            {
                "query": "Web scraping project: navigate with Playwright, save data to files, search conversation history for similar projects",
                "expected_servers": ["playwright", "filesystem", "conversation-search"]
            },
            {
                "query": "Component library maintenance: convert components with Mitosis, create Storybook stories, organize documentation",
                "expected_servers": ["mitosis", "storybook", "document-organizer"]
            },
            {
                "query": "Project analysis: scan file system, check git history, search GitHub for references, generate telemetry report",
                "expected_servers": ["filesystem", "git", "github", "claude-telemetry"]
            }
        ]

        results = []
        for scenario in multi_server_scenarios:
            retrieved_tools = retriever.get_relevant_tools(scenario["query"], k=8)

            # Analyze server distribution
            servers_used = set()
            for tool in retrieved_tools:
                # Find the server for this tool
                for original_tool in tools:
                    if original_tool["name"] == tool.name:
                        servers_used.add(original_tool["server"])
                        break

            expected_servers = set(scenario["expected_servers"])
            server_coverage = len(servers_used.intersection(expected_servers)) / len(expected_servers)

            result = {
                "query": scenario["query"],
                "expected_servers": scenario["expected_servers"],
                "servers_found": list(servers_used),
                "server_coverage": server_coverage,
                "tools_retrieved": [tool.name for tool in retrieved_tools]
            }
            results.append(result)

            print(f"\\nQuery: {scenario['query'][:60]}...")
            print(f"  Expected servers: {scenario['expected_servers']}")
            print(f"  Found servers: {list(servers_used)}")
            print(f"  Coverage: {server_coverage:.2f}")

        avg_coverage = sum(r["server_coverage"] for r in results) / len(results)
        print(f"\\nAverage server coverage: {avg_coverage:.2f}")

        return {
            "multi_server_results": results,
            "avg_server_coverage": avg_coverage
        }

    def _get_directory_size(self, path: str) -> int:
        """Get total size of directory in bytes"""
        total = 0
        try:
            for entry in os.scandir(path):
                if entry.is_file():
                    total += entry.stat().st_size
                elif entry.is_dir():
                    total += self._get_directory_size(entry.path)
        except (OSError, IOError):
            pass
        return total

    async def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run all comprehensive tests"""
        print("Starting Comprehensive RAG Test Suite with Real MCP Tools")
        print("=" * 70)
        print(f"Test environment: {self.temp_dir}")

        # Run all tests
        self.test_results = {}

        self.test_results["ingestion"] = self.test_ingestion_with_comprehensive_tools()
        self.test_results["complex_retrieval"] = self.test_complex_retrieval_scenarios()
        self.test_results["scalability"] = self.test_scalability_with_comprehensive_dataset()
        self.test_results["token_efficiency"] = self.test_token_efficiency()
        self.test_results["multi_server"] = self.test_multi_server_scenarios()

        # Generate comprehensive report
        self._generate_comprehensive_report()

        print("\\n" + "=" * 70)
        print("All comprehensive tests completed!")
        print(f"Detailed report saved to: {self.temp_dir}/comprehensive_test_report.json")
        print("=" * 70)
        print(f"Test environment preserved at: {self.temp_dir}")

        return self.test_results

    def _generate_comprehensive_report(self):
        """Generate a comprehensive test report"""
        report_path = os.path.join(self.temp_dir, "comprehensive_test_report.json")

        summary = {
            "test_summary": {
                "total_tools_tested": self.test_results["ingestion"]["tools_processed"],
                "servers_covered": self.test_results["ingestion"]["servers_covered"],
                "avg_f1_score": self.test_results["complex_retrieval"]["overall_metrics"]["avg_f1_score"],
                "token_savings_pct": self.test_results["token_efficiency"]["savings_percentage"],
                "server_coverage": self.test_results["multi_server"]["avg_server_coverage"]
            },
            "detailed_results": self.test_results
        }

        with open(report_path, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"\\n=== Comprehensive Test Summary ===")
        print(f"Tools tested: {summary['test_summary']['total_tools_tested']}")
        print(f"Servers covered: {summary['test_summary']['servers_covered']}")
        print(f"Average F1 score: {summary['test_summary']['avg_f1_score']:.3f}")
        print(f"Token savings: {summary['test_summary']['token_savings_pct']:.1f}%")
        print(f"Multi-server coverage: {summary['test_summary']['server_coverage']:.2f}")

async def main():
    tester = ComprehensiveRAGTester()
    await tester.run_comprehensive_tests()

if __name__ == "__main__":
    asyncio.run(main())