# RAG Validation Test Suite

This directory contains comprehensive tests for validating the RAG tool filtering system in MetaMCP-RAG.

## Test Structure

### 1. Simple Integration Test (`test-rag-integration-simple.js`)

**Purpose:** Basic infrastructure and connection testing

**Tests:**
- ✅ MCP server connection status
- ✅ RAG service health check
- ✅ Test server availability (TEST1-TEST5)
- ✅ Tool discovery functionality
- ✅ Sample query processing

**Usage:**
```bash
# Run simple integration test
npm run test:rag

# Or directly
node test-rag-integration-simple.js
```

### 2. Comprehensive Validation Suite (`rag-validation-tests.js`)

**Purpose:** Full RAG system validation with performance metrics

**Test Categories:**
- **Semantic Filtering:** 11 test scenarios across 5 categories
- **Performance Testing:** Concurrent and sequential processing
- **Tool Availability:** 15 tools across MATH, FILE, TEXT, DATA, SYSTEM
- **Graceful Fallback:** Behavior when RAG service unavailable

**Usage:**
```bash
# Run full validation suite
npm run test:rag-full

# Or directly
node rag-validation-tests.js
```

## Test Scenarios

### Semantic Tool Selection Tests

| Test ID | Query | Expected Category | Expected Tools |
|---------|-------|------------------|----------------|
| MATH-001 | "Calculate the square root of 64" | MATH | test_calculate |
| MATH-002 | "Convert 100 pounds to kilograms" | MATH | test_convert_units, test_statistics |
| FILE-001 | "Read my configuration file" | FILE | test_read_file, test_list_files |
| FILE-002 | "Write data to a new file" | FILE | test_write_file |
| TEXT-001 | "Format this text properly" | TEXT | test_format_text, test_extract_keywords |
| TEXT-002 | "Summarize the content" | TEXT | test_summarize |
| DATA-001 | "Generate sample user data" | DATA | test_generate_data |
| DATA-002 | "Create sample dataset" | DATA | test_create_sample, test_mock_api |
| SYSTEM-001 | "Check system memory usage" | SYSTEM | test_system_status, test_environment |
| SYSTEM-002 | "Run diagnostics" | SYSTEM | test_diagnostics |
| MIXED-001 | "Generate data, save to file, check status" | MIXED | Multiple categories |

### Performance Test Scenarios

| Test ID | Description | Expected Latency | Queries |
|---------|-------------|------------------|---------|
| PERF-001 | Concurrent query handling | <50ms | 5 simultaneous queries |
| PERF-002 | Sequential query processing | <50ms each | 5 sequential queries |

## Success Criteria

### 1. Semantic Accuracy
- **90%+ category matching** - Queries select correct tool categories
- **Tool relevance** - Expected tools included in filtered results

### 2. Context Reduction
- **Target: 77.8% reduction** - 15 tools → 3-5 relevant tools
- **Minimum: 50% reduction** - Significant context savings

### 3. Performance
- **<50ms average latency** - Fast tool selection
- **Concurrent handling** - Multiple simultaneous queries
- **Graceful degradation** - Works when RAG service down

### 4. Infrastructure
- **MCP server connectivity** - metamcp-rag server connected
- **Test server availability** - All 5 test servers built and ready
- **RAG service health** - HTTP service responding correctly

## Expected Tool Categories

### MATH (3 tools)
- `test_calculate` - Basic mathematical calculations
- `test_convert_units` - Unit conversion operations
- `test_statistics` - Statistical analysis

### FILE (3 tools)
- `test_read_file` - File reading operations
- `test_write_file` - File writing operations
- `test_list_files` - Directory listing

### TEXT (3 tools)
- `test_format_text` - Text formatting operations
- `test_extract_keywords` - Keyword extraction
- `test_summarize` - Text summarization

### DATA (3 tools)
- `test_generate_data` - Data generation
- `test_create_sample` - Sample dataset creation
- `test_mock_api` - API response mocking

### SYSTEM (3 tools)
- `test_system_status` - System status checking
- `test_environment` - Environment information
- `test_diagnostics` - System diagnostics

## Running Tests

### Prerequisites
```bash
# Ensure MCP servers are connected
claude mcp list

# Should show:
# ✓ metamcp-rag: Connected
# ✓ filesystem: Connected
```

### Quick Test
```bash
npm run test:rag
```

### Full Validation
```bash
npm run test:rag-full
```

### Manual Test Steps
1. **Infrastructure Check:** Verify MCP servers connected
2. **RAG Service:** Check http://localhost:8002/health responds
3. **Test Servers:** Confirm all 5 test servers built
4. **Tool Discovery:** Test MetaMCP-RAG responds to MCP protocol
5. **Query Testing:** Run sample queries across all categories

## Interpreting Results

### ✅ Success Indicators
- All tests pass (100% pass rate)
- Average latency <50ms
- Context reduction ≥77.8%
- All 15 tools available across 5 categories

### ⚠️ Warning Signs
- Pass rate <90%
- Latency >50ms average
- Context reduction <50%
- Missing test servers or tools

### ❌ Failure Scenarios
- MCP server not connected
- RAG service unavailable
- Test servers not built
- Tool discovery failing

## Next Steps After Testing

### If All Tests Pass ✅
- System ready for production RAG validation
- Can proceed with real MCP server integration
- Ready for performance optimization testing

### If Tests Fail ❌
1. **Check MCP Connection:** `claude mcp list`
2. **Verify RAG Service:** `curl http://localhost:8002/health`
3. **Build Test Servers:** Check test-servers build status
4. **Review Logs:** Check server startup logs for errors

## Test Architecture

The test suite is designed with:
- **Modular Structure** - Each test category independent
- **Real Integration** - Uses actual MCP protocol communication
- **Performance Measurement** - Latency and throughput metrics
- **Graceful Error Handling** - Continues testing on individual failures
- **Comprehensive Reporting** - Detailed pass/fail analysis

This validates the complete RAG integration pipeline from infrastructure through semantic filtering to performance characteristics.