import { Tool } from "@modelcontextprotocol/sdk/types.js";

import { ragClient, RAGServiceError } from "../../rag/rag-client";
import {
  ListToolsMiddleware,
  MetaMCPHandlerContext,
} from "./functional-middleware";

/**
 * Configuration for the RAG middleware
 */
export interface RAGToolsConfig {
  enabled?: boolean;
  maxTools?: number;
  similarityThreshold?: number;
  fallbackOnError?: boolean;
  timeout?: number;
}

/**
 * Creates a List Tools middleware that uses RAG for semantic tool selection
 * This replaces static tool loading with intelligent, query-based selection
 */
export function createRAGListToolsMiddleware(
  config: RAGToolsConfig = {}
): ListToolsMiddleware {
  const {
    enabled = true,
    maxTools = 10,
    similarityThreshold = 0.0,
    fallbackOnError = true,
    timeout = 5000,
  } = config;

  return (handler) => {
    return async (request, context: MetaMCPHandlerContext) => {
      // Call the original handler to get all available tools
      const response = await handler(request, context);

      // If RAG is disabled or no tools to filter, return original response
      if (!enabled || !response.tools || response.tools.length === 0) {
        return response;
      }

      try {
        // Extract user intent from context
        // In a real implementation, this would come from the user's request context
        // For now, we'll use a generic query - this should be enhanced based on
        // how MetaMCP tracks user intent/session context
        const userQuery = extractUserIntentFromContext(request, context);

        console.log(
          `RAG: Filtering ${response.tools.length} tools for query: "${userQuery}"`
        );

        // Use RAG to select most relevant tools
        const selectedTools = await ragClient.selectTools(
          userQuery,
          response.tools,
          maxTools,
          similarityThreshold
        );

        console.log(
          `RAG: Selected ${selectedTools.length}/${response.tools.length} tools`
        );

        return {
          ...response,
          tools: selectedTools,
        };

      } catch (error) {
        console.error("RAG tool selection failed:", error);

        if (fallbackOnError) {
          console.log("RAG: Falling back to original tool list");
          // Return original tools, possibly limited
          const limitedTools = response.tools.slice(0, maxTools);
          return {
            ...response,
            tools: limitedTools,
          };
        } else {
          throw error;
        }
      }
    };
  };
}

/**
 * Extract user intent from request/context
 * This is a simplified implementation - in practice, this would be more sophisticated
 */
function extractUserIntentFromContext(
  request: any,
  context: MetaMCPHandlerContext
): string {
  // Try to extract meaningful intent from various sources

  // 1. If there's a specific tool being called, use that as context
  if (request?.params?.name) {
    return `Find tools related to: ${request.params.name}`;
  }

  // 2. Check for any query parameters or hints
  if (request?.params?.query) {
    return request.params.query;
  }

  // 3. Check context for user session information
  if (context?.sessionId) {
    // In a real implementation, we might look up recent user activity
    // from the session to understand current workflow
  }

  // 4. Check for namespace context - different namespaces might have different use cases
  if (context?.namespaceUuid) {
    // Could map namespace to typical use cases
    return "Select tools for current namespace workflow";
  }

  // 5. Default fallback query
  return "Select the most commonly used and essential tools";
}

/**
 * Enhanced RAG middleware that combines status filtering with semantic selection
 * This can be used alongside the existing filter-tools middleware
 */
export function createEnhancedRAGMiddleware(
  ragConfig: RAGToolsConfig = {},
  statusFilterEnabled: boolean = true
): ListToolsMiddleware {
  const ragMiddleware = createRAGListToolsMiddleware(ragConfig);

  return (handler) => {
    const ragHandler = ragMiddleware(handler);

    return async (request, context) => {
      // First apply RAG filtering
      const ragResponse = await ragHandler(request, context);

      // If status filtering is disabled, return RAG results
      if (!statusFilterEnabled) {
        return ragResponse;
      }

      // Additional status filtering could be applied here
      // For now, we'll just return the RAG-filtered results
      // In practice, you might want to combine this with the existing
      // filter-tools middleware for status-based filtering

      return ragResponse;
    };
  };
}