/**
 * RAG Tool Selection Client
 *
 * TypeScript client for communicating with the Python RAG service
 * Provides semantic tool selection for MetaMCP middleware
 */

import { Tool } from "@modelcontextprotocol/sdk/types.js";

export interface ToolSelectionRequest {
  query: string;
  available_tools: string[];
  limit?: number;
  similarity_threshold?: number;
}

export interface ToolSelectionResponse {
  selected_tools: string[];
  scores: number[];
  query: string;
  total_available: number;
  total_selected: number;
}

export interface RAGServiceStats {
  tool_count: number;
  vector_db_path: string;
  embedding_model: string;
}

export interface RAGClientConfig {
  baseUrl: string;
  enabled: boolean;
  fallbackOnError: boolean;
  timeout: number;
  defaultLimit: number;
  defaultThreshold: number;
}

export class RAGServiceError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public originalError?: Error
  ) {
    super(message);
    this.name = "RAGServiceError";
  }
}

export class RAGClient {
  private config: RAGClientConfig;
  private healthyCache: boolean | null = null;
  private lastHealthCheck = 0;
  private readonly HEALTH_CACHE_DURATION = 30000; // 30 seconds

  constructor(config: Partial<RAGClientConfig> = {}) {
    this.config = {
      baseUrl: process.env.RAG_SERVICE_URL || "http://127.0.0.1:8002",
      enabled: process.env.RAG_SERVICE_ENABLED !== "false",
      fallbackOnError: true,
      timeout: 5000,
      defaultLimit: 10,
      defaultThreshold: 0.0,
      ...config,
    };
  }

  /**
   * Check if RAG service is healthy
   */
  async isHealthy(): Promise<boolean> {
    const now = Date.now();

    // Use cached result if recent
    if (this.healthyCache !== null && (now - this.lastHealthCheck) < this.HEALTH_CACHE_DURATION) {
      return this.healthyCache;
    }

    try {
      const response = await fetch(`${this.config.baseUrl}/health`, {
        method: "GET",
        timeout: this.config.timeout,
      });

      const healthy = response.ok;
      this.healthyCache = healthy;
      this.lastHealthCheck = now;

      return healthy;
    } catch (error) {
      this.healthyCache = false;
      this.lastHealthCheck = now;
      return false;
    }
  }

  /**
   * Get RAG service statistics
   */
  async getStats(): Promise<RAGServiceStats> {
    if (!this.config.enabled) {
      throw new RAGServiceError("RAG service is disabled");
    }

    try {
      const response = await fetch(`${this.config.baseUrl}/stats`, {
        method: "GET",
        timeout: this.config.timeout,
      });

      if (!response.ok) {
        throw new RAGServiceError(
          `RAG service error: ${response.status} ${response.statusText}`,
          response.status
        );
      }

      return await response.json();
    } catch (error) {
      if (error instanceof RAGServiceError) {
        throw error;
      }
      throw new RAGServiceError(
        "Failed to get RAG service stats",
        undefined,
        error as Error
      );
    }
  }

  /**
   * Select most relevant tools based on user query
   */
  async selectTools(
    query: string,
    availableTools: Tool[],
    limit?: number,
    similarityThreshold?: number
  ): Promise<Tool[]> {
    // If RAG is disabled, return all tools (up to limit)
    if (!this.config.enabled) {
      const actualLimit = limit ?? this.config.defaultLimit;
      return availableTools.slice(0, actualLimit);
    }

    // Check service health first
    const isHealthy = await this.isHealthy();
    if (!isHealthy) {
      if (this.config.fallbackOnError) {
        console.warn("RAG service unhealthy, falling back to all tools");
        const actualLimit = limit ?? this.config.defaultLimit;
        return availableTools.slice(0, actualLimit);
      } else {
        throw new RAGServiceError("RAG service is not available");
      }
    }

    try {
      const request: ToolSelectionRequest = {
        query,
        available_tools: availableTools.map(tool => tool.name),
        limit: limit ?? this.config.defaultLimit,
        similarity_threshold: similarityThreshold ?? this.config.defaultThreshold,
      };

      const response = await fetch(`${this.config.baseUrl}/select-tools`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(request),
        timeout: this.config.timeout,
      });

      if (!response.ok) {
        throw new RAGServiceError(
          `RAG tool selection failed: ${response.status} ${response.statusText}`,
          response.status
        );
      }

      const result: ToolSelectionResponse = await response.json();

      // Map selected tool names back to tool objects
      const selectedTools: Tool[] = [];
      for (const toolName of result.selected_tools) {
        const tool = availableTools.find(t => t.name === toolName);
        if (tool) {
          selectedTools.push(tool);
        }
      }

      console.log(
        `RAG selected ${selectedTools.length}/${availableTools.length} tools for query: "${query}"`
      );

      return selectedTools;

    } catch (error) {
      if (error instanceof RAGServiceError) {
        if (this.config.fallbackOnError) {
          console.error("RAG tool selection failed, falling back to all tools:", error.message);
          const actualLimit = limit ?? this.config.defaultLimit;
          return availableTools.slice(0, actualLimit);
        } else {
          throw error;
        }
      }

      // Network or other unexpected errors
      if (this.config.fallbackOnError) {
        console.error("Unexpected error in RAG tool selection, falling back:", error);
        const actualLimit = limit ?? this.config.defaultLimit;
        return availableTools.slice(0, actualLimit);
      } else {
        throw new RAGServiceError(
          "RAG tool selection failed",
          undefined,
          error as Error
        );
      }
    }
  }

  /**
   * Create a user query from request context
   * This extracts intent from MCP request details
   */
  static extractQueryFromContext(
    request: any,
    context: any
  ): string {
    // Try to extract meaningful query from request
    if (request?.params?.name) {
      return `Tool needed for: ${request.params.name}`;
    }

    // Fallback to generic query
    return "Select relevant tools for current task";
  }
}

// Global RAG client instance
export const ragClient = new RAGClient();