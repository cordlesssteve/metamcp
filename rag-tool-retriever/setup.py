#!/usr/bin/env python3
"""
Setup script for MetaMCP RAG Tool Retriever

This script automates the installation and setup of the RAG system.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def run_command(command, description="Running command"):
    """Run a shell command with error handling"""
    print(f"{description}: {command}")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        if e.stderr:
            print(f"stderr: {e.stderr}")
        return False

def install_dependencies():
    """Install required Python packages"""
    print("Installing Python dependencies...")

    # Check if pip is available
    if not run_command("pip --version", "Checking pip"):
        print("Error: pip is not available. Please install pip first.")
        return False

    # Install requirements
    if not run_command("pip install -r requirements.txt", "Installing requirements"):
        print("Failed to install requirements. You may need to install manually.")
        return False

    print("✓ Dependencies installed successfully")
    return True

def setup_directories():
    """Create necessary directories"""
    print("Setting up directories...")

    directories = [
        "./chroma_db",
        "./logs",
        "./data",
        "./exports"
    ]

    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {directory}")

    return True

def test_embeddings():
    """Test that the embedding model can be loaded"""
    print("Testing embedding model...")

    test_code = '''
import sys
try:
    from langchain.embeddings import HuggingFaceEmbeddings
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    print("✓ Embedding model loaded successfully")
    sys.exit(0)
except Exception as e:
    print(f"✗ Error loading embedding model: {e}")
    sys.exit(1)
'''

    try:
        result = subprocess.run([sys.executable, "-c", test_code],
                              capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print(result.stdout)
            return True
        else:
            print(result.stderr)
            return False
    except subprocess.TimeoutExpired:
        print("✗ Embedding model test timed out")
        return False

def create_sample_data():
    """Create sample tool data for testing"""
    print("Creating sample data...")

    sample_tools = [
        {
            "name": "read_file",
            "description": "Read the contents of a file from the filesystem",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to read"}
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
                    "repo_path": {"type": "string", "description": "Path to git repository"}
                }
            }
        },
        {
            "name": "web_search",
            "description": "Search the web for information",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {"type": "integer", "description": "Maximum results"}
                },
                "required": ["query"]
            }
        }
    ]

    import json
    with open("./data/sample_tools.json", "w") as f:
        json.dump(sample_tools, f, indent=2)

    print("✓ Sample data created: ./data/sample_tools.json")
    return True

def run_initial_ingestion():
    """Run initial tool ingestion with sample data"""
    print("Running initial tool ingestion...")

    if not run_command("python ingest.py --sample-tools --persist-dir ./chroma_db",
                      "Ingesting sample tools"):
        print("Failed to run initial ingestion")
        return False

    print("✓ Initial ingestion completed")
    return True

def verify_installation():
    """Verify that everything is working"""
    print("Verifying installation...")

    # Test retrieval
    test_code = '''
import sys
try:
    from retriever import ToolRetriever
    retriever = ToolRetriever("./chroma_db")
    info = retriever.get_database_info()
    print(f"✓ Database info: {info}")

    # Test retrieval
    tools = retriever.get_relevant_tools("read a file", k=2)
    print(f"✓ Retrieved {len(tools)} tools for test query")
    sys.exit(0)
except Exception as e:
    print(f"✗ Error during verification: {e}")
    sys.exit(1)
'''

    try:
        result = subprocess.run([sys.executable, "-c", test_code],
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(result.stdout)
            return True
        else:
            print(result.stderr)
            return False
    except subprocess.TimeoutExpired:
        print("✗ Verification test timed out")
        return False

def main():
    """Main setup function"""
    parser = argparse.ArgumentParser(description="Setup MetaMCP RAG Tool Retriever")
    parser.add_argument("--skip-deps", action="store_true",
                       help="Skip dependency installation")
    parser.add_argument("--skip-test", action="store_true",
                       help="Skip verification tests")
    parser.add_argument("--quick", action="store_true",
                       help="Quick setup (skip embeddings test)")

    args = parser.parse_args()

    print("MetaMCP RAG Tool Retriever Setup")
    print("=" * 40)

    success = True

    # Install dependencies
    if not args.skip_deps:
        success &= install_dependencies()

    # Setup directories
    success &= setup_directories()

    # Test embeddings (unless quick mode)
    if not args.quick:
        success &= test_embeddings()

    # Create sample data
    success &= create_sample_data()

    # Run initial ingestion
    success &= run_initial_ingestion()

    # Verify installation
    if not args.skip_test:
        success &= verify_installation()

    print("\n" + "=" * 40)
    if success:
        print("✓ Setup completed successfully!")
        print("\nNext steps:")
        print("1. Run 'python test_rag_system.py' to test the complete system")
        print("2. Use 'python ingest.py' to index your own tools")
        print("3. Use 'python retriever.py \"your query\"' to test retrieval")
        print("4. Integrate with metaMCP using integration_example.py")
    else:
        print("✗ Setup encountered errors. Please check the output above.")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())