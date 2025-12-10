# AgentHub Product Roadmap
## SaaS & On-Premises Deployment Strategy

---

## Vision
AgentHub is an enterprise-ready AI agent orchestration platform that can be deployed as:
- **SaaS**: Multi-tenant AWS deployment (managed service)
- **On-Premises**: Single-tenant deployable package (Docker/Kubernetes)

---

## Feature Priority Matrix

### Phase 1: MVP Foundation (Completed)
*Core platform functionality*

| Feature | Status | Description |
|---------|--------|-------------|
| Agent CRUD | Done | Create, read, update, delete agents |
| Chat Interface | Done | Real-time agent conversations |
| MCP Integration | Done | AWS S3 bucket tools |
| RAG/Knowledge Base | Done | Document upload & vector search |
| User Authentication | Done | Signup, login, sessions |
| CloudWatch/Datadog | Done | External monitoring integrations |
| Profile Management | Done | Settings, region, API keys, logout |
| Dark/Light Theme | Done | Theme toggle |

---

### Phase 2: SaaS Readiness (In Progress)
*Features required for multi-tenant SaaS deployment*

| # | Feature | Priority | Effort | Status |
|---|---------|----------|--------|--------|
| 2.1 | Chat History & Sessions | P0 | Medium | Done - Database tables, API endpoints |
| 2.2 | Agent Templates | P0 | Low | Done - 6 pre-built templates |
| 2.3 | Multi-Model Support | P0 | Low | Done - API endpoint with 4 models |
| 2.4 | Template Picker UI | P0 | Medium | Done - Modal with grid layout |
| 2.5 | Usage Analytics Dashboard | P1 | High | Done - Full analytics page |
| 2.6 | Streaming Responses | P1 | Medium | Pending |
| 2.7 | Rate Limiting | P1 | Medium | Pending |
| 2.8 | Tenant Isolation | P1 | High | Pending |
| 2.9 | Billing Integration (Stripe) | P2 | High | Pending |
| 2.10 | Admin Dashboard | P2 | High | Pending |

---

### Phase 3: Enterprise Features (Next Quarter)
*Features for enterprise on-prem customers*

| # | Feature | Priority | Effort | Status |
|---|---------|----------|--------|--------|
| 3.1 | SSO (SAML, OAuth, OIDC) | P0 | High | Pending |
| 3.2 | Role-Based Access Control (RBAC) | P0 | High | Pending |
| 3.3 | Audit Logging | P1 | Medium | Pending |
| 3.4 | Data Encryption at Rest | P1 | Medium | Pending |
| 3.5 | Air-Gapped Deployment Support | P2 | High | Pending |
| 3.6 | LDAP/Active Directory | P2 | High | Pending |
| 3.7 | Custom Branding (White-label) | P3 | Medium | Pending |

---

### Phase 4: Advanced AI Capabilities (Future)
*Differentiation features*

| # | Feature | Priority | Effort | Status |
|---|---------|----------|--------|--------|
| 4.1 | Agent Workflows (Multi-agent chains) | P1 | High | Pending |
| 4.2 | Agent Marketplace | P2 | High | Pending |
| 4.3 | Prompt A/B Testing | P2 | Medium | Pending |
| 4.4 | Agent Memory (Long-term) | P2 | High | Pending |
| 4.5 | Fine-tuning Integration | P3 | Very High | Pending |
| 4.6 | Voice Input/Output | P3 | High | Pending |

---

### Phase 5: Developer Experience (Ongoing)
*API & SDK improvements*

| # | Feature | Priority | Effort | Status |
|---|---------|----------|--------|--------|
| 5.1 | API Documentation Page | P1 | Medium | Pending |
| 5.2 | Comprehensive Docs | P1 | Medium | Done - documents/ folder |
| 5.3 | Webhook Support | P2 | Medium | Pending |
| 5.4 | Python SDK | P2 | Medium | Pending |
| 5.5 | JavaScript SDK | P3 | Medium | Pending |
| 5.6 | CLI Tool | P3 | Medium | Pending |

---

## Completed Features Summary

### Backend
- [x] FastAPI REST API server
- [x] SQLite database (agents, users, sessions, templates)
- [x] Chat sessions and messages persistence
- [x] Agent templates (6 pre-built)
- [x] Multi-model support API
- [x] User authentication (signup, login, logout)
- [x] Session management with tokens
- [x] Integration settings storage
- [x] CloudWatch & Datadog monitoring
- [x] MCP Server with S3 tools
- [x] RAG with Milvus vector store
- [x] PDF document processing

### Frontend
- [x] Dashboard (index.html) - Agent cards overview
- [x] Orchestrator (orchestrator.html) - Agent config & chat
- [x] Chat (chat.html) - Standalone chat interface
- [x] Integrations (integrations.html) - AWS/Datadog setup
- [x] Analytics (analytics.html) - Usage dashboard
- [x] Login (login.html) - Authentication UI
- [x] Profile dropdown with menu
- [x] Template picker modal
- [x] Region selector modal
- [x] API keys modal
- [x] Dark/Light theme toggle
- [x] Responsive sidebar navigation

### Documentation
- [x] ARCHITECTURE.md - System architecture
- [x] API.md - Complete API reference
- [x] DATABASE.md - Schema documentation
- [x] FLOWS.md - User & data flows
- [x] SETUP.md - Installation guide
- [x] ROADMAP.md - Product roadmap

---

## Pending Features (Priority Order)

### High Priority (This Week)
1. **Streaming Responses** - Real-time token-by-token display
2. **Rate Limiting** - Per-user API limits
3. **Docker Compose** - On-prem deployment package

### Medium Priority (Next 2 Weeks)
4. **Google OAuth** - SSO login
5. **RBAC Foundations** - Admin/User roles
6. **API Documentation Page** - Interactive API explorer
7. **Chat History UI** - Sidebar with past sessions (Done - Basic UI)
8. **Advanced RAG Intent Detection** - Use LLM for smarter query classification
9. **Load & Resume Chat Sessions** - Click on history item to load full conversation (requires DB storage optimization)

### Lower Priority (Future)
10. SDKs (Python, JavaScript)
11. **User Preferences Sync** - Sync UI preferences (theme, last selected agent) across devices via server

---

## Architecture Decisions for SaaS/On-Prem

### Database Strategy
```
SaaS Mode:
-- PostgreSQL (AWS RDS) - Primary database
-- Redis (ElastiCache) - Caching & sessions
-- Milvus/Pinecone - Vector store (managed)
-- S3 - File storage

On-Prem Mode:
-- PostgreSQL (Docker) - Primary database
-- Redis (Docker) - Caching & sessions
-- Milvus Lite - Vector store (embedded)
-- MinIO - S3-compatible storage
```

### Configuration Management
```yaml
# config.yaml
deployment_mode: saas | onprem
database:
  type: postgres
  host: ${DB_HOST}
  ssl: true
storage:
  type: s3 | minio
  bucket: agenthub-data
auth:
  providers: [email, google, saml]
  session_ttl: 24h
features:
  multi_tenancy: true
  rate_limiting: true
  analytics: true
```

### Docker Compose (On-Prem)
```yaml
# docker-compose.yml
services:
  agenthub:
    image: agenthub/core:latest
    ports: ["8000:8000"]
  postgres:
    image: postgres:15
  redis:
    image: redis:7
  milvus:
    image: milvusdb/milvus:latest
```

---

## Success Metrics

### SaaS KPIs
- Monthly Active Users (MAU)
- Agent creation rate
- Messages per user per day
- API call volume
- Churn rate
- MRR (Monthly Recurring Revenue)

### On-Prem KPIs
- Deployment success rate
- Time to first agent
- Support ticket volume
- Upgrade adoption rate

---

## Timeline

| Phase | Target | Status | Milestone |
|-------|--------|--------|-----------|
| Phase 1 | Dec 2024 | Complete | MVP Launch |
| Phase 2 | Jan 2025 | In Progress | SaaS Beta |
| Phase 3 | Q1 2025 | Pending | Enterprise GA |
| Phase 4 | Q2 2025 | Pending | AI Features |
| Phase 5 | Ongoing | Partial | Developer Platform |

---

## Progress Tracker

```
Phase 1: [##########] 100% Complete
Phase 2: [######----]  60% Complete
Phase 3: [----------]   0% Complete
Phase 4: [----------]   0% Complete
Phase 5: [##--------]  20% Complete
```

---

*Last Updated: December 7, 2024*
