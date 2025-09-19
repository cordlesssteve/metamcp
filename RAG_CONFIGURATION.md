# RAG Integration Configuration Guide

## Overview

The RAG (Retrieval-Augmented Generation) integration provides semantic tool selection for MetaMCP, reducing context window usage by intelligently selecting the most relevant tools based on user intent.

## Architecture

```
┌─────────────────┐    HTTP     ┌─────────────────┐    Vector    ┌─────────────────┐
│ TypeScript      │ ◄────────── │ Python RAG      │ ◄────────── │ ChromaDB        │
│ MetaMCP Backend │             │ Service         │             │ Vector Store    │
└─────────────────┘             └─────────────────┘             └─────────────────┘
        │                               │                               │
        │ Middleware Pipeline           │ Tool Selection                │ Embeddings
        │                               │                               │
        ▼                               ▼                               ▼
┌─────────────────┐             ┌─────────────────┐             ┌─────────────────┐
│ 1. RAG Filter   │             │ Semantic        │             │ Tool Definitions│
│ 2. Status Filter│             │ Similarity      │             │ + Descriptions  │
│ 3. Tool Response│             │ Search          │             │                 │
└─────────────────┘             └─────────────────┘             └─────────────────┘
```

## Environment Variables

### MetaMCP Backend Configuration

Add these environment variables to your MetaMCP backend:

```bash
# RAG Service Configuration
RAG_ENABLED=true                          # Enable/disable RAG integration
RAG_SERVICE_URL=http://127.0.0.1:8002     # URL of the Python RAG service
RAG_MAX_TOOLS=10                          # Maximum tools to return per query
RAG_SIMILARITY_THRESHOLD=0.0              # Minimum similarity score (0.0-2.0)

# RAG Service Health
RAG_SERVICE_ENABLED=true                  # Enable RAG service calls
```

### Python RAG Service Configuration

```bash
# Service Configuration
RAG_SERVICE_HOST=127.0.0.1               # Host to bind the service
RAG_SERVICE_PORT=8002                    # Port for the RAG service

# Performance Configuration
RAG_VECTOR_DB_PATH=./real_tools_db       # Path to ChromaDB vector database
RAG_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2  # Embedding model
```

## Installation Steps

### 1. Python RAG Service Setup

```bash
# Navigate to RAG directory
cd rag-tool-retriever

# Install dependencies
./venv/bin/pip install fastapi uvicorn langchain chromadb sentence-transformers langchain-community

# Start the service
./venv/bin/python rag_service.py
```

### 2. MetaMCP Backend Integration

The RAG middleware is automatically integrated into the MetaMCP proxy when environment variables are set.

### 3. Verify Integration

```bash
# Check RAG service health
curl http://127.0.0.1:8002/health

# Check service stats
curl http://127.0.0.1:8002/stats

# Test tool selection
curl -X POST http://127.0.0.1:8002/select-tools \
  -H "Content-Type: application/json" \
  -d '{
    "query": "convert PDF files",
    "available_tools": ["convert_pdf", "check_dependency"],
    "limit": 5
  }'
```

## Configuration Options

### RAG Middleware Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `enabled` | `true` | Enable RAG filtering |
| `maxTools` | `10` | Maximum tools per response |
| `similarityThreshold` | `0.0` | Minimum similarity score |
| `fallbackOnError` | `true` | Return all tools if RAG fails |
| `timeout` | `5000` | RAG service timeout (ms) |

### Performance Tuning

#### Context Window Optimization

- **Conservative**: `RAG_MAX_TOOLS=5` - Aggressive context reduction
- **Balanced**: `RAG_MAX_TOOLS=10` - Good performance/utility balance
- **Comprehensive**: `RAG_MAX_TOOLS=20` - More tools, larger context

#### Similarity Threshold Tuning

- **Permissive**: `RAG_SIMILARITY_THRESHOLD=0.0` - Include all semantically related tools
- **Moderate**: `RAG_SIMILARITY_THRESHOLD=0.5` - Only moderately similar tools
- **Strict**: `RAG_SIMILARITY_THRESHOLD=1.0` - Only highly similar tools

## Deployment Modes

### Development Mode

```bash
# Single-instance, local development
RAG_ENABLED=true
RAG_SERVICE_URL=http://127.0.0.1:8002
```

### Production Mode

```bash
# Separate service deployment
RAG_ENABLED=true
RAG_SERVICE_URL=http://rag-service:8002
RAG_SERVICE_TIMEOUT=3000
```

### Fallback Mode

```bash
# RAG disabled, traditional tool loading
RAG_ENABLED=false
```

## Monitoring and Troubleshooting

### Health Checks

```bash
# RAG service health
curl http://127.0.0.1:8002/health

# Expected response:
{
  "status": "healthy",
  "retriever_available": true,
  "vector_db_path": "real_tools_db"
}
```

### Common Issues

1. **RAG Service Not Available**
   - Check service is running: `ps aux | grep rag_service`
   - Verify port not blocked: `curl http://127.0.0.1:8002/health`
   - Check logs for Python errors

2. **No Tools Selected**
   - Verify tools are in vector database: `curl http://127.0.0.1:8002/stats`
   - Check similarity threshold (lower = more permissive)
   - Ensure tool names match between MetaMCP and RAG service

3. **Performance Issues**
   - Reduce `RAG_MAX_TOOLS` for faster responses
   - Increase `RAG_SERVICE_TIMEOUT` for complex queries
   - Monitor RAG service resource usage

### Logging

The RAG integration provides structured logging:

```typescript
// MetaMCP logs
console.log(`RAG selected ${selectedTools.length}/${availableTools.length} tools for query: "${query}"`);

// RAG service logs
logger.info(f"Query: '{query}' -> Selected {len(selected_tools)}/{len(available_tools)} tools");
```

## Migration Guide

### From Static Tool Loading

1. **Enable RAG gradually**:
   ```bash
   RAG_ENABLED=true
   RAG_MAX_TOOLS=50  # Start with high limit
   ```

2. **Monitor performance**:
   - Check response times
   - Verify tool selection quality
   - Monitor context window usage

3. **Optimize settings**:
   - Reduce `RAG_MAX_TOOLS` gradually
   - Adjust similarity threshold based on results
   - Fine-tune for your use cases

### Rollback Plan

```bash
# Instant rollback - disable RAG
RAG_ENABLED=false

# Graceful degradation - high tool limit
RAG_MAX_TOOLS=100
RAG_SIMILARITY_THRESHOLD=0.0
```

## Development Workflow

### Adding New Tools

1. **Update tool definitions**: Add new tools to `real_mcp_tools.json`
2. **Rebuild vector database**: Restart RAG service to reload tools
3. **Test semantic matching**: Use `/select-tools` endpoint to verify

### Custom Tool Queries

The RAG system extracts user intent from request context. To improve matching:

1. **Enhance query extraction**: Modify `extractUserIntentFromContext()`
2. **Add session context**: Include user workflow information
3. **Custom embeddings**: Train domain-specific embedding models

## API Reference

### RAG Service Endpoints

#### `GET /health`
Check service health and availability.

#### `GET /stats`
Get service statistics and configuration.

#### `POST /select-tools`
Select relevant tools based on user query.

**Request:**
```json
{
  "query": "string",
  "available_tools": ["string"],
  "limit": 10,
  "similarity_threshold": 0.0
}
```

**Response:**
```json
{
  "selected_tools": ["string"],
  "scores": [0.8, 0.6],
  "query": "string",
  "total_available": 5,
  "total_selected": 2
}
```