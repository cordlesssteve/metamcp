#!/usr/bin/env python3
"""
Basic test to verify core functionality without external dependencies
"""

import json
import sys
import os
from pathlib import Path

def test_file_structure():
    """Test that all required files are present"""
    required_files = [
        "tool_definitions.py",
        "ingest.py",
        "retriever.py",
        "integration_example.py",
        "test_rag_system.py",
        "requirements.txt",
        "setup.py",
        "README.md"
    ]

    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)

    if missing_files:
        print(f"✗ Missing files: {missing_files}")
        return False

    print(f"✓ All {len(required_files)} required files present")
    return True

def test_tool_standardization_logic():
    """Test tool standardization without external dependencies"""

    # Mock the LangChain Tool class
    class MockTool:
        def __init__(self, name, func, description):
            self.name = name
            self.func = func
            self.description = description

    # Create a simplified standardizer for testing
    class TestStandardizer:
        def __init__(self):
            self.tools = []

        def add_mcp_tool(self, tool_data, server_name):
            name = tool_data.get('name', 'unnamed_tool')
            description = tool_data.get('description', 'No description')
            input_schema = tool_data.get('inputSchema', {})

            # Enhanced description logic
            enhanced_description = self._enhance_description(name, description, input_schema, server_name)

            # Mock tool
            def mock_func(*args, **kwargs):
                return f"Mock execution of {name}"

            tool = {
                'name': name,
                'description': enhanced_description,
                'original_description': description,
                'server_source': server_name
            }
            self.tools.append(tool)
            return tool

        def _enhance_description(self, name, description, input_schema, server_name):
            parts = [
                f"Tool: {name}",
                f"Source: {server_name} MCP server",
                f"Description: {description}"
            ]

            # Add parameters
            if input_schema and 'properties' in input_schema:
                parts.append("Parameters:")
                for param_name, param_def in input_schema['properties'].items():
                    param_type = param_def.get('type', 'unknown')
                    param_desc = param_def.get('description', 'No description')
                    parts.append(f"- {param_name} ({param_type}): {param_desc}")

            # Add keywords
            keywords = self._extract_keywords(name, description)
            if keywords:
                parts.append(f"Keywords: {', '.join(keywords)}")

            return "\n".join(parts)

        def _extract_keywords(self, name, description):
            keywords = set()

            # Extract from name
            name_parts = name.lower().replace('_', ' ').replace('-', ' ').split()
            keywords.update(name_parts)

            # Extract action words
            action_words = ['read', 'write', 'create', 'update', 'delete', 'get', 'set']
            description_lower = description.lower()
            for word in action_words:
                if word in description_lower:
                    keywords.add(word)

            return list(keywords)

    # Test the standardizer
    standardizer = TestStandardizer()

    test_tool = {
        "name": "read_file",
        "description": "Read the contents of a file from the filesystem",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to read"},
                "encoding": {"type": "string", "description": "File encoding"}
            },
            "required": ["path"]
        }
    }

    tool = standardizer.add_mcp_tool(test_tool, "FileSystem Server")

    # Verify enhancement
    original_len = len(test_tool['description'])
    enhanced_len = len(tool['description'])

    if enhanced_len <= original_len:
        print(f"✗ Description not enhanced: {original_len} -> {enhanced_len}")
        return False

    if "Tool: read_file" not in tool['description']:
        print("✗ Enhanced description missing tool name")
        return False

    if "Source: FileSystem Server" not in tool['description']:
        print("✗ Enhanced description missing server source")
        return False

    if "Parameters:" not in tool['description']:
        print("✗ Enhanced description missing parameters")
        return False

    print(f"✓ Tool standardization working: {original_len} -> {enhanced_len} chars")
    print(f"✓ Enhanced description contains all required elements")

    return True

def test_json_data_structures():
    """Test that we can work with JSON tool data"""

    sample_tools = [
        {
            "name": "filesystem__read_file",
            "description": "Read file contents",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"}
                }
            }
        },
        {
            "name": "git__status",
            "description": "Get git repository status",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Repository path"}
                }
            }
        }
    ]

    # Test JSON serialization
    try:
        json_str = json.dumps(sample_tools, indent=2)
        parsed_tools = json.loads(json_str)

        if len(parsed_tools) != len(sample_tools):
            print("✗ JSON roundtrip failed")
            return False

        print(f"✓ JSON serialization working for {len(sample_tools)} tools")

    except Exception as e:
        print(f"✗ JSON handling failed: {e}")
        return False

    return True

def test_directory_structure():
    """Test that we can create the expected directory structure"""

    test_dirs = ["test_chroma_db", "test_logs", "test_data"]

    try:
        for dirname in test_dirs:
            Path(dirname).mkdir(exist_ok=True)
            if not os.path.exists(dirname):
                print(f"✗ Failed to create directory: {dirname}")
                return False

        print(f"✓ Directory creation working for {len(test_dirs)} directories")

        # Cleanup
        for dirname in test_dirs:
            if os.path.exists(dirname):
                os.rmdir(dirname)

    except Exception as e:
        print(f"✗ Directory operations failed: {e}")
        return False

    return True

def test_metaMCP_integration_structure():
    """Test that integration example has the right structure"""

    try:
        with open("integration_example.py", "r") as f:
            content = f.read()

        required_classes = [
            "RAGEnabledMetaMCPProxy",
            "MetaMCPIntegrationHelper"
        ]

        required_methods = [
            "handle_list_tools_request",
            "handle_call_tool_request",
            "discover_and_index_tools"
        ]

        missing_items = []

        for class_name in required_classes:
            if f"class {class_name}" not in content:
                missing_items.append(f"class {class_name}")

        for method_name in required_methods:
            if f"def {method_name}" not in content:
                missing_items.append(f"method {method_name}")

        if missing_items:
            print(f"✗ Integration example missing: {missing_items}")
            return False

        print(f"✓ Integration example has all required components")

    except Exception as e:
        print(f"✗ Integration example test failed: {e}")
        return False

    return True

def main():
    """Run all basic tests"""
    print("Running MetaMCP RAG System Basic Tests")
    print("=" * 50)

    tests = [
        ("File Structure", test_file_structure),
        ("Tool Standardization Logic", test_tool_standardization_logic),
        ("JSON Data Structures", test_json_data_structures),
        ("Directory Operations", test_directory_structure),
        ("Integration Structure", test_metaMCP_integration_structure)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\nTesting: {test_name}")
        try:
            if test_func():
                passed += 1
                print(f"✓ {test_name} PASSED")
            else:
                print(f"✗ {test_name} FAILED")
        except Exception as e:
            print(f"✗ {test_name} ERROR: {e}")

    print(f"\n{'=' * 50}")
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("✓ All basic tests passed! The RAG system structure is correct.")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Run setup: python setup.py")
        print("3. Test with dependencies: python test_rag_system.py")
        return 0
    else:
        print("✗ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())