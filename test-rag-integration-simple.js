#!/usr/bin/env node

/**
 * Simple RAG Integration Test
 *
 * Tests the actual MetaMCP-RAG server integration with real MCP calls
 */

import { exec } from 'child_process';
import { promisify } from 'util';
import { performance } from 'perf_hooks';

const execAsync = promisify(exec);

class SimpleRAGTest {
  constructor() {
    this.testResults = [];
  }

  /**
   * Test if MetaMCP-RAG server is accessible and returns tools
   */
  async testMCPConnection() {
    console.log('🔗 Testing MCP server connection...');

    try {
      // Test that Claude Code can see the metamcp-rag server
      const { stdout } = await execAsync('claude mcp list');

      const isConnected = stdout.includes('metamcp-rag') && stdout.includes('✓ Connected');

      const result = {
        test: 'MCP Connection',
        passed: isConnected,
        details: isConnected ? 'MetaMCP-RAG server connected' : 'MetaMCP-RAG server not connected',
        timestamp: new Date().toISOString()
      };

      this.testResults.push(result);
      console.log(`   ${result.passed ? '✅' : '❌'} ${result.details}`);

      return result;

    } catch (error) {
      const result = {
        test: 'MCP Connection',
        passed: false,
        details: `Connection failed: ${error.message}`,
        timestamp: new Date().toISOString()
      };

      this.testResults.push(result);
      console.log(`   ❌ ${result.details}`);

      return result;
    }
  }

  /**
   * Test RAG service availability
   */
  async testRAGService() {
    console.log('🧠 Testing RAG service availability...');

    try {
      // Check if RAG service responds to health check
      const { stdout } = await execAsync('curl -s http://localhost:8002/health');

      const isHealthy = stdout.includes('status') || stdout.includes('healthy');

      const result = {
        test: 'RAG Service Health',
        passed: isHealthy,
        details: isHealthy ? 'RAG service responding' : 'RAG service not responding',
        response: stdout.substring(0, 100),
        timestamp: new Date().toISOString()
      };

      this.testResults.push(result);
      console.log(`   ${result.passed ? '✅' : '❌'} ${result.details}`);

      return result;

    } catch (error) {
      const result = {
        test: 'RAG Service Health',
        passed: false,
        details: `RAG service unavailable: ${error.message}`,
        timestamp: new Date().toISOString()
      };

      this.testResults.push(result);
      console.log(`   ❌ ${result.details}`);

      return result;
    }
  }

  /**
   * Test individual test servers are working
   */
  async testTestServers() {
    console.log('🧪 Testing individual test servers...');

    const testServers = ['test1', 'test2', 'test3', 'test4', 'test5'];
    const serverResults = [];

    for (const server of testServers) {
      try {
        const serverPath = `/home/cordlesssteve/mcp-servers/servers/src/metamcp-rag/test-servers/${server}`;

        // Check if test server directory exists and has proper structure
        const { stdout } = await execAsync(`ls -la ${serverPath}/dist/ 2>/dev/null || echo "missing"`);

        const exists = !stdout.includes('missing') && stdout.includes('index.js');

        const result = {
          test: `Test Server ${server}`,
          passed: exists,
          details: exists ? `${server} built and ready` : `${server} missing or not built`,
          timestamp: new Date().toISOString()
        };

        serverResults.push(result);
        console.log(`   ${result.passed ? '✅' : '❌'} ${result.details}`);

      } catch (error) {
        const result = {
          test: `Test Server ${server}`,
          passed: false,
          details: `Error checking ${server}: ${error.message}`,
          timestamp: new Date().toISOString()
        };

        serverResults.push(result);
        console.log(`   ❌ ${result.details}`);
      }
    }

    this.testResults.push(...serverResults);
    return serverResults;
  }

  /**
   * Test real tool discovery through MetaMCP-RAG
   */
  async testToolDiscovery() {
    console.log('🔍 Testing real tool discovery through MetaMCP-RAG...');

    try {
      const startTime = performance.now();

      // Test real tool discovery via MCP protocol
      const discoveryResult = await this.testRealToolDiscovery();

      const endTime = performance.now();
      const latency = endTime - startTime;

      const result = {
        test: 'Real Tool Discovery',
        passed: discoveryResult.success,
        toolCount: discoveryResult.toolCount,
        expectedTools: 15, // 5 servers × 3 tools each
        details: discoveryResult.success
          ? `Discovered ${discoveryResult.toolCount} tools from test servers`
          : `Tool discovery failed: ${discoveryResult.error || 'No tools found'}`,
        latency: latency,
        timestamp: new Date().toISOString()
      };

      this.testResults.push(result);

      if (result.passed) {
        console.log(`   ✅ ${result.details} (${latency.toFixed(2)}ms)`);

        if (result.toolCount !== result.expectedTools) {
          console.log(`   ⚠️  Expected ${result.expectedTools} tools, found ${result.toolCount}`);
        }
      } else {
        console.log(`   ❌ ${result.details}`);
      }

      return result;

    } catch (error) {
      const result = {
        test: 'Real Tool Discovery',
        passed: false,
        details: `Tool discovery failed: ${error.message}`,
        timestamp: new Date().toISOString()
      };

      this.testResults.push(result);
      console.log(`   ❌ ${result.details}`);

      return result;
    }
  }

  /**
   * Test real tool discovery via MCP protocol
   */
  async testRealToolDiscovery() {
    try {
      // Test using MCP client to discover tools
      const initMessage = JSON.stringify({
        jsonrpc: "2.0",
        method: "initialize",
        params: {
          protocolVersion: "2024-11-05",
          capabilities: {},
          clientInfo: { name: "test-client", version: "1.0.0" }
        },
        id: 1
      });

      const listToolsMessage = JSON.stringify({
        jsonrpc: "2.0",
        method: "tools/list",
        params: {},
        id: 2
      });

      const combinedInput = initMessage + '\n' + listToolsMessage + '\n';

      const { stdout } = await execAsync(
        `echo '${combinedInput}' | timeout 40 mcp-server-metamcp-rag`
      );

      // Check if we got tool discovery results
      const hasInitResponse = stdout.includes('"id":1') && stdout.includes('result');
      const hasToolsResponse = stdout.includes('"id":2') && stdout.includes('tools');

      // Count discovered tools
      const toolMatches = stdout.match(/"name":"test_[^"]+"/g);
      const toolCount = toolMatches ? toolMatches.length : 0;

      return {
        success: hasInitResponse && hasToolsResponse,
        toolCount: toolCount,
        rawOutput: stdout
      };

    } catch (error) {
      console.log(`   ⚠️  Real tool discovery failed: ${error.message}`);
      return { success: false, toolCount: 0, error: error.message };
    }
  }

  /**
   * Helper to ping MetaMCP server
   */
  async pingMetaMCPServer() {
    const discoveryResult = await this.testRealToolDiscovery();
    return discoveryResult.success;
  }

  /**
   * Test real tool call execution
   */
  async testRealToolCall() {
    console.log('🔧 Testing real tool call execution...');

    try {
      // Test a real tool call through MCP protocol
      const toolCallMessage = JSON.stringify({
        jsonrpc: "2.0",
        method: "tools/call",
        params: {
          name: "test_write_file",
          arguments: {
            filename: "test-integration.txt",
            content: "Hello from RAG integration test!"
          }
        },
        id: 3
      });

      const initMessage = JSON.stringify({
        jsonrpc: "2.0",
        method: "initialize",
        params: {
          protocolVersion: "2024-11-05",
          capabilities: {},
          clientInfo: { name: "test-client", version: "1.0.0" }
        },
        id: 1
      });

      const combinedInput = initMessage + '\n' + toolCallMessage + '\n';

      const startTime = performance.now();

      const { stdout } = await execAsync(
        `echo '${combinedInput}' | timeout 25 mcp-server-metamcp-rag`
      );

      const endTime = performance.now();
      const latency = endTime - startTime;

      // Check if tool call succeeded
      const hasResult = stdout.includes('"id":3') && stdout.includes('result');
      const hasError = stdout.includes('error');

      const result = {
        test: 'Real Tool Call',
        passed: hasResult && !hasError,
        details: hasResult ? 'Tool call executed successfully' : 'Tool call failed or no response',
        latency: latency,
        rawOutput: stdout.substring(0, 200) + '...',
        timestamp: new Date().toISOString()
      };

      this.testResults.push(result);
      console.log(`   ${result.passed ? '✅' : '❌'} ${result.details} (${latency.toFixed(2)}ms)`);

      return result;

    } catch (error) {
      const result = {
        test: 'Real Tool Call',
        passed: false,
        details: `Tool call failed: ${error.message}`,
        timestamp: new Date().toISOString()
      };

      this.testResults.push(result);
      console.log(`   ❌ ${result.details}`);

      return result;
    }
  }

  /**
   * Generate test report
   */
  generateReport() {
    const total = this.testResults.length;
    const passed = this.testResults.filter(r => r.passed).length;
    const failed = total - passed;
    const passRate = (passed / total) * 100;

    const avgLatency = this.testResults
      .filter(r => r.latency)
      .reduce((sum, r, _, arr) => sum + r.latency / arr.length, 0);

    return {
      summary: {
        totalTests: total,
        passed: passed,
        failed: failed,
        passRate: passRate,
        avgLatency: avgLatency || 0,
        timestamp: new Date().toISOString()
      },
      results: this.testResults,
      status: failed === 0 ? 'ALL_PASSED' : 'SOME_FAILED'
    };
  }

  /**
   * Run all tests
   */
  async runTests() {
    console.log('🚀 Starting Simple RAG Integration Tests');
    console.log('=' .repeat(50));

    try {
      // Test 1: MCP Connection
      await this.testMCPConnection();

      // Test 2: RAG Service
      await this.testRAGService();

      // Test 3: Test Servers
      await this.testTestServers();

      // Test 4: Tool Discovery
      await this.testToolDiscovery();

      // Test 5: Real Tool Call
      await this.testRealToolCall();

      // Generate Report
      const report = this.generateReport();

      console.log('\n' + '=' .repeat(50));
      console.log('📊 TEST RESULTS SUMMARY');
      console.log('=' .repeat(50));
      console.log(`Total Tests: ${report.summary.totalTests}`);
      console.log(`Passed: ${report.summary.passed}`);
      console.log(`Failed: ${report.summary.failed}`);
      console.log(`Pass Rate: ${report.summary.passRate.toFixed(1)}%`);

      if (report.summary.avgLatency > 0) {
        console.log(`Average Latency: ${report.summary.avgLatency.toFixed(2)}ms`);
      }

      console.log(`Overall Status: ${report.status}`);

      if (report.status === 'ALL_PASSED') {
        console.log('\n✅ All tests passed! System ready for RAG validation.');
      } else {
        console.log('\n⚠️  Some tests failed. Review results above.');

        const failedTests = this.testResults.filter(r => !r.passed);
        console.log('\nFailed Tests:');
        failedTests.forEach(test => {
          console.log(`  • ${test.test}: ${test.details}`);
        });
      }

      return report;

    } catch (error) {
      console.error('❌ Test execution failed:', error);
      throw error;
    }
  }
}

// Export for use in other scripts
export { SimpleRAGTest };

// Run if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  const test = new SimpleRAGTest();

  test.runTests()
    .then(report => {
      process.exit(report.status === 'ALL_PASSED' ? 0 : 1);
    })
    .catch(error => {
      console.error('❌ Test execution failed:', error);
      process.exit(1);
    });
}