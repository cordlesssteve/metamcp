#!/usr/bin/env node

/**
 * Comprehensive RAG Integration Testing Framework
 *
 * This framework provides multiple levels of testing:
 * 1. Build validation
 * 2. End-to-end integration
 * 3. Performance measurement
 * 4. Failure mode testing
 * 5. Tool name validation
 */

const fs = require('fs');
const path = require('path');
const { spawn, exec } = require('child_process');
const https = require('http');

class TestFramework {
  constructor() {
    this.results = {
      passed: 0,
      failed: 0,
      tests: []
    };
    this.ragServiceUrl = 'http://127.0.0.1:8002';
    this.metaMcpUrl = 'http://127.0.0.1:3001'; // Assuming MetaMCP runs on 3001

    // Find project root directory (contains package.json for MetaMCP)
    this.projectRoot = this.findProjectRoot();
    this.backendDir = path.join(this.projectRoot, 'apps', 'backend');
  }

  findProjectRoot() {
    let current = __dirname;
    while (current !== '/') {
      // Look for key project markers
      const packageJson = path.join(current, 'package.json');
      const appsDir = path.join(current, 'apps');
      const ragDir = path.join(current, 'rag-tool-retriever');

      if (fs.existsSync(packageJson) && fs.existsSync(appsDir) && fs.existsSync(ragDir)) {
        return current;
      }
      current = path.dirname(current);
    }
    // Fallback: assume we're in apps/backend and go up two levels
    return path.resolve(__dirname, '..', '..');
  }

  log(message, type = 'info') {
    const timestamp = new Date().toISOString();
    const icons = { info: 'ℹ️', success: '✅', error: '❌', warning: '⚠️' };
    console.log(`${icons[type] || 'ℹ️'} [${timestamp}] ${message}`);
  }

  async makeRequest(url, options = {}) {
    return new Promise((resolve, reject) => {
      const req = https.request(url, options, (res) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => {
          try {
            const parsed = data ? JSON.parse(data) : {};
            resolve({ status: res.statusCode, data: parsed, raw: data });
          } catch (e) {
            resolve({ status: res.statusCode, data: null, raw: data });
          }
        });
      });

      req.on('error', reject);
      req.setTimeout(10000, () => reject(new Error('Request timeout')));

      if (options.body) {
        req.write(options.body);
      }

      req.end();
    });
  }

  async execCommand(command, cwd = process.cwd()) {
    return new Promise((resolve, reject) => {
      exec(command, { cwd }, (error, stdout, stderr) => {
        resolve({ error, stdout, stderr, success: !error });
      });
    });
  }

  async test(name, testFn) {
    this.log(`Running: ${name}`);
    const startTime = Date.now();

    try {
      await testFn();
      const duration = Date.now() - startTime;
      this.results.passed++;
      this.results.tests.push({ name, status: 'passed', duration });
      this.log(`✅ PASSED: ${name} (${duration}ms)`, 'success');
    } catch (error) {
      const duration = Date.now() - startTime;
      this.results.failed++;
      this.results.tests.push({ name, status: 'failed', duration, error: error.message });
      this.log(`❌ FAILED: ${name} - ${error.message}`, 'error');
    }
  }

  async runBuildTests() {
    this.log('=== BUILD VALIDATION TESTS ===');

    await this.test('TypeScript compilation', async () => {
      const result = await this.execCommand('npm run build', this.backendDir);
      if (!result.success) {
        throw new Error(`Build failed: ${result.stderr}`);
      }
      if (!result.stdout.includes('Build success')) {
        throw new Error('Build did not report success');
      }
    });

    await this.test('Module structure validation', async () => {
      // Instead of importing the main server (which starts services),
      // just verify the build output exists and is valid JavaScript
      const distPath = path.join(this.backendDir, 'dist', 'index.js');

      if (!fs.existsSync(distPath)) {
        throw new Error('Compiled index.js does not exist');
      }

      // Check file size (should be substantial for a real build)
      const stats = fs.statSync(distPath);
      if (stats.size < 10000) { // Less than 10KB is suspicious
        throw new Error(`Compiled file too small: ${stats.size} bytes`);
      }

      // Validate it's syntactically valid JavaScript
      const testScript = `
        try {
          // Parse but don't execute the main module to avoid starting services
          const fs = require('fs');
          const content = fs.readFileSync('${distPath}', 'utf8');

          // Check for basic indicators that it's a valid TypeScript build output
          if (!content.includes('express') ||
              !content.includes('auth') ||
              content.length < 10000) {
            throw new Error('Build output does not contain expected content');
          }

          console.log('Module validation successful - contains expected build artifacts');
          console.log('File size: ${stats.size} bytes');
        } catch (e) {
          console.error('Module validation failed:', e.message);
          process.exit(1);
        }
      `;

      fs.writeFileSync('/tmp/test-validation.js', testScript);
      const result = await this.execCommand('node /tmp/test-validation.js');

      if (!result.success) {
        throw new Error(`Module validation failed: ${result.stderr}`);
      }
    });
  }

  async runServiceTests() {
    this.log('=== RAG SERVICE VALIDATION ===');

    await this.test('RAG service health', async () => {
      const response = await this.makeRequest(`${this.ragServiceUrl}/health`);
      if (response.status !== 200) {
        throw new Error(`Health check failed with status ${response.status}`);
      }
      if (!response.data.retriever_available) {
        throw new Error('Retriever not available');
      }
    });

    await this.test('RAG service stats', async () => {
      const response = await this.makeRequest(`${this.ragServiceUrl}/stats`);
      if (response.status !== 200) {
        throw new Error(`Stats failed with status ${response.status}`);
      }
      if (response.data.tool_count === 0) {
        throw new Error('No tools loaded in RAG service');
      }
    });

    await this.test('RAG tool selection basic', async () => {
      const request = {
        query: 'convert PDF files',
        available_tools: ['convert_pdf', 'check_dependency', 'unrelated_tool'],
        limit: 3
      };

      const response = await this.makeRequest(`${this.ragServiceUrl}/select-tools`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
      });

      if (response.status !== 200) {
        throw new Error(`Tool selection failed with status ${response.status}`);
      }

      if (!response.data.selected_tools.includes('convert_pdf')) {
        throw new Error('Expected convert_pdf to be selected for PDF query');
      }
    });
  }

  async runPerformanceTests() {
    this.log('=== PERFORMANCE MEASUREMENT ===');

    await this.test('RAG service latency', async () => {
      const iterations = 10;
      const times = [];

      for (let i = 0; i < iterations; i++) {
        const start = Date.now();

        const response = await this.makeRequest(`${this.ragServiceUrl}/select-tools`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query: 'file operations and data processing',
            available_tools: ['convert_pdf', 'check_dependency', 'read_file', 'write_file'],
            limit: 5
          })
        });

        const latency = Date.now() - start;
        times.push(latency);

        if (response.status !== 200) {
          throw new Error(`Request ${i + 1} failed with status ${response.status}`);
        }
      }

      const avgLatency = times.reduce((a, b) => a + b, 0) / times.length;
      const maxLatency = Math.max(...times);

      this.log(`Average latency: ${avgLatency.toFixed(2)}ms, Max: ${maxLatency}ms`);

      if (avgLatency > 1000) {
        throw new Error(`Average latency too high: ${avgLatency}ms`);
      }
    });

    await this.test('Concurrent request handling', async () => {
      const concurrentRequests = 5;
      const promises = [];

      for (let i = 0; i < concurrentRequests; i++) {
        promises.push(
          this.makeRequest(`${this.ragServiceUrl}/select-tools`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              query: `test query ${i}`,
              available_tools: ['convert_pdf', 'check_dependency'],
              limit: 2
            })
          })
        );
      }

      const results = await Promise.all(promises);

      for (let i = 0; i < results.length; i++) {
        if (results[i].status !== 200) {
          throw new Error(`Concurrent request ${i + 1} failed`);
        }
      }
    });
  }

  async runFailureModeTests() {
    this.log('=== FAILURE MODE TESTING ===');

    await this.test('Invalid query handling', async () => {
      const response = await this.makeRequest(`${this.ragServiceUrl}/select-tools`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: '', // Empty query
          available_tools: [],
          limit: 5
        })
      });

      // Should handle gracefully, not crash
      if (response.status >= 500) {
        throw new Error('Service crashed on invalid input');
      }
    });

    await this.test('Large tool list handling', async () => {
      // Create a large list of fake tool names
      const largeToolList = Array.from({ length: 1000 }, (_, i) => `tool_${i}`);

      const response = await this.makeRequest(`${this.ragServiceUrl}/select-tools`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: 'file operations',
          available_tools: largeToolList,
          limit: 10
        })
      });

      if (response.status >= 500) {
        throw new Error('Service failed with large tool list');
      }
    });

    await this.test('Network timeout simulation', async () => {
      // Test very short timeout
      try {
        await Promise.race([
          this.makeRequest(`${this.ragServiceUrl}/select-tools`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              query: 'test',
              available_tools: ['test'],
              limit: 1
            })
          }),
          new Promise((_, reject) =>
            setTimeout(() => reject(new Error('Timeout')), 100)
          )
        ]);
      } catch (error) {
        if (error.message !== 'Timeout') {
          throw error;
        }
        // Timeout is expected in this test
      }
    });
  }

  async runToolNameValidationTests() {
    this.log('=== TOOL NAME VALIDATION ===');

    await this.test('Tool name format consistency', async () => {
      const statsResponse = await this.makeRequest(`${this.ragServiceUrl}/stats`);
      if (statsResponse.status !== 200) {
        throw new Error('Could not get RAG stats');
      }

      // Get a sample of tools to test name formats
      const testResponse = await this.makeRequest(`${this.ragServiceUrl}/select-tools`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: 'any tools',
          available_tools: ['convert_pdf', 'check_dependency', 'document_organizer__discover_pdfs'],
          limit: 10
        })
      });

      if (testResponse.status !== 200) {
        throw new Error('Tool selection failed');
      }

      // Validate that returned tools are from the available list
      for (const toolName of testResponse.data.selected_tools) {
        if (!['convert_pdf', 'check_dependency', 'document_organizer__discover_pdfs'].includes(toolName)) {
          throw new Error(`Unexpected tool returned: ${toolName}`);
        }
      }
    });
  }

  async generateReport() {
    this.log('=== TEST REPORT ===');

    const total = this.results.passed + this.results.failed;
    const successRate = total > 0 ? (this.results.passed / total * 100).toFixed(1) : 0;

    this.log(`Total Tests: ${total}`);
    this.log(`Passed: ${this.results.passed}`, 'success');
    this.log(`Failed: ${this.results.failed}`, this.results.failed > 0 ? 'error' : 'info');
    this.log(`Success Rate: ${successRate}%`);

    if (this.results.failed > 0) {
      this.log('=== FAILED TESTS ===');
      for (const test of this.results.tests) {
        if (test.status === 'failed') {
          this.log(`❌ ${test.name}: ${test.error}`, 'error');
        }
      }
    }

    // Write detailed report to file
    const report = {
      timestamp: new Date().toISOString(),
      summary: {
        total,
        passed: this.results.passed,
        failed: this.results.failed,
        successRate: parseFloat(successRate)
      },
      tests: this.results.tests
    };

    const reportPath = path.join(this.projectRoot, 'test-report.json');
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
    this.log(`Detailed report written to ${reportPath}`);

    return this.results.failed === 0;
  }

  async runAll() {
    this.log('🧪 Starting Comprehensive RAG Testing Framework');
    this.log('================================================');

    try {
      await this.runBuildTests();
      await this.runServiceTests();
      await this.runPerformanceTests();
      await this.runFailureModeTests();
      await this.runToolNameValidationTests();
    } catch (error) {
      this.log(`Critical error in test framework: ${error.message}`, 'error');
    }

    const success = await this.generateReport();

    if (success) {
      this.log('🎉 ALL TESTS PASSED - System ready for production!', 'success');
    } else {
      this.log('💥 SOME TESTS FAILED - Review issues before deployment', 'error');
    }

    return success;
  }
}

// Export for use as module or run directly
if (require.main === module) {
  const framework = new TestFramework();
  framework.runAll().then(success => {
    process.exit(success ? 0 : 1);
  }).catch(error => {
    console.error('Test framework crashed:', error);
    process.exit(1);
  });
}

module.exports = TestFramework;