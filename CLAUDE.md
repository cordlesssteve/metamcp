# MetaMCP-RAG Project Configuration

## Universal Standards (Imports)
@../../../.claude/config/intellectual-honesty.md
@../../../.claude/config/verification-protocols.md
@../../../.claude/config/file-organization.md

## [Fallback] Core Standards
*If imports above fail, these provide essential behavioral guidelines:*
- Plan Status Indicators (ACTIVE/ARCHIVED/SUPERSEDED/BLOCKED)
- Critical Success Verification (compilation, instantiation, integration)
- Red Flag warnings for documentation conflicts

## 🚨 MANDATORY READING ORDER 🚨
Before starting ANY development work, Claude MUST read these files in order:

1. **[CURRENT_STATUS.md](./CURRENT_STATUS.md)** - Current reality and what's actually done
2. **[ACTIVE_PLAN.md](./ACTIVE_PLAN.md)** - What we're currently executing
3. Only then reference other documentation for context

## Project Context
- **Platform:** MetaMCP (MCP Proxy/Aggregator) with RAG-based tool retrieval enhancement
- **Current Version:** v1.0.0 (Production Ready)
- **Active Branch:** feature/rag-tool-retriever (ready for merge/deployment)
- **Focus:** RAG integration complete - context optimization for MCP tool selection

## Architecture Overview

### Core Components
- **MetaMCP Backend** (`apps/backend/`) - Express.js + tRPC MCP proxy server
- **RAG Tool Retriever** (`rag-tool-retriever/`) - Python FastAPI service for semantic tool selection
- **Vector Database** - ChromaDB with 54 real MCP tools indexed
- **Integration Layer** - TypeScript client bridging MetaMCP ↔ RAG service

### Key Technology Stack
- **Backend:** Node.js 20+, TypeScript, Express 5.1, tRPC, Better Auth
- **RAG Service:** Python 3.8+, FastAPI, ChromaDB, LangChain, sentence-transformers
- **Database:** PostgreSQL (Better Auth), ChromaDB (vector embeddings)
- **Infrastructure:** Docker Compose, Nginx-ready SSE configuration

## Development Commands

### Essential Development Workflow
```bash
# Start full system (with PostgreSQL)
docker compose up -d

# Development mode (backend + frontend)
pnpm dev

# RAG service (standalone)
cd rag-tool-retriever && python rag_service.py

# Testing suite
pnpm test                                    # Framework tests
node e2e-integration-test.cjs               # E2E integration tests
./apps/backend/test-framework.cjs           # Comprehensive backend tests
```

### Critical Build/Validation Commands
```bash
# TypeScript compilation check (MANDATORY before claiming "ready")
pnpm build

# Backend compilation specifically
cd apps/backend && pnpm build

# Lint and format
pnpm lint

# RAG service health check
curl http://localhost:8002/health
```

## Key File Locations

### Core Integration Files
- `apps/backend/src/lib/rag/rag-client.ts` - TypeScript RAG client
- `apps/backend/src/lib/metamcp/metamcp-middleware/rag-tools.functional.ts` - RAG middleware
- `apps/backend/src/lib/metamcp/metamcp-proxy.ts` - Main proxy with RAG integration
- `rag-tool-retriever/rag_service.py` - Python FastAPI RAG HTTP service

### Configuration Files
- `.env` / `.env.local` - Environment configuration (RAG_ENABLED, RAG_SERVICE_URL)
- `docker-compose.yml` - Production Docker setup
- `package.json` - Workspace configuration
- `turbo.json` - Monorepo build configuration

### Testing Infrastructure
- `apps/backend/test-framework.cjs` - Comprehensive test framework
- `e2e-integration-test.cjs` - End-to-end integration validation
- `test-rag-integration.js` - RAG-specific integration tests

## Environment Configuration

### Required Environment Variables
```bash
# RAG Service Configuration
RAG_ENABLED=true                           # Enable/disable RAG middleware
RAG_SERVICE_URL=http://localhost:8002      # RAG HTTP service endpoint
RAG_MAX_TOOLS=10                          # Maximum tools to select
RAG_SIMILARITY_THRESHOLD=0.1              # Minimum similarity score

# MetaMCP Core
APP_URL=http://localhost:12008             # Frontend URL
DATABASE_URL=postgresql://...             # PostgreSQL connection
```

### Port Configuration
- **12008** - Frontend (Next.js)
- **12009** - Backend (Express.js + tRPC)
- **8002** - RAG Service (FastAPI)
- **5432** - PostgreSQL (Docker)

## Testing Standards

### Verification Gates (MANDATORY)
Before claiming ANY component "ready" or "working":
1. **Compilation Gate** - `pnpm build` must succeed with zero errors
2. **Instantiation Gate** - Core services must start and respond to health checks
3. **Integration Gate** - RAG ↔ MetaMCP communication must work end-to-end

### Test Suite Requirements
- **Framework Tests:** 90%+ success rate expected (currently 95.5%)
- **E2E Integration:** 100% success with graceful fallback testing
- **Performance Validation:** Context reduction >70%, latency <50ms

## RAG System Specifics

### RAG Integration Architecture
- **HTTP Bridge Pattern** - Python RAG service ↔ TypeScript MetaMCP client
- **Middleware Integration** - RAG tool filtering in MetaMCP proxy pipeline
- **Graceful Fallback** - System works normally if RAG service unavailable
- **Vector Database** - ChromaDB with sentence-transformers embeddings

### RAG Service Capabilities
- **Semantic Tool Selection** - Query-based tool filtering using vector similarity
- **Context Optimization** - 77.8% reduction in tool context (9 tools → 2 tools)
- **Performance** - 19ms average latency, handles 5+ concurrent requests
- **Health Monitoring** - `/health`, `/stats` endpoints for observability

## Security & Production Considerations

### Security Requirements
- **Never commit** API keys or secrets to repository
- **Use environment variable references** (`${VAR_NAME}`) in configurations
- **Validate RAG service availability** before production deployment
- **CORS configuration** properly set for production domains

### Production Deployment Notes
- **RAG service** must be running before MetaMCP backend starts
- **Vector database** (ChromaDB) requires persistent storage
- **SSE configuration** requires Nginx proxy setup (see nginx.conf.example)
- **Health checks** essential for container orchestration

## Emergency Procedures

### RAG Service Failure
1. Check RAG service health: `curl http://localhost:8002/health`
2. Restart RAG service: `cd rag-tool-retriever && python rag_service.py`
3. Verify vector database: Check `rag-tool-retriever/real_tools_db/` exists
4. MetaMCP continues operating (fallback mode) even with RAG service down

### MetaMCP Backend Issues
1. Check compilation: `cd apps/backend && pnpm build`
2. Verify environment variables in `.env.local`
3. Check PostgreSQL connectivity
4. Review logs: `docker compose logs backend`

## Documentation Rules

### Plan Status Indicators - ALWAYS CHECK THESE
- **ACTIVE**: Currently executing - use this plan
- **ARCHIVED**: Completed/historical - reference only
- **SUPERSEDED**: Replaced by newer plan - ignore unless needed for context
- **BLOCKED**: Waiting for external input - cannot proceed

### Red Flags 🚨
**STOP and ask for clarification if you see:**
- Multiple plans marked as "ACTIVE"
- Conflicting information between CURRENT_STATUS.md and ACTIVE_PLAN.md
- Plans that haven't been updated in >1 week
- Missing status headers on planning documents

## Development Standards Integration
- **ALWAYS follow** Universal Project Documentation Standard v2.0
- **NEVER deviate** from established Git configuration patterns
- **ALWAYS implement** Five-Level Testing Maturity Model
- **MINIMUM requirement** - Level 3 (90% coverage, automated critical paths)