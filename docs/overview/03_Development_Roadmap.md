**Title**: Development Roadmap and Milestones
**Version**: v1.2
**Status**: CURRENT
**Last reviewed**: 2026-04-19
**Related docs**:
- Charter: `docs/overview/NEXUSCORE_PRODUCT_CHARTER.md`
- SRS: `docs/srs/NEXUSCORE_SRS.md`
- Governance: `docs/governance/NEXUSCORE_GOVERNANCE.md`
- CR Specs: `docs/spec/`
- Overview Index: `docs/overview/00_OVERVIEW_INDEX.md`

---

# NexusCore Development Roadmap

## Current Achievements

| Metric | Value |
|---|---|
| Test Coverage | 80.22% |
| Test Cases | 4,838 |
| LLM Providers | GPT-5.5 / Sonnet 4.6 / Gemini 3.1 Pro / GLM-5.1 / MiniMax M2.7 |
| Agents | 18+ specialized agents |
| Core Modules | NPE (Security Engine), FKB (Fault Knowledge Base) |

---

## Phase 1: Foundation Integration and Hardening

**Goal**: Establish a robust single-architecture system with Orchestrator as the sole brain, complete self-healing cycles, and automate quality enforcement.

### Milestones

- **Month 1**: Architecture integration and duplicate functionality removal
- **Month 2**: Self-healing cycle automation (execute -> detect -> FKB lookup -> auto-fix -> retest)
- **Month 3**: Quality gate implementation and automated coverage improvement loop

### Definition of Done

- **MC1-1**: Zero CLI/API/UI access paths bypassing the single Orchestrator
- **MC1-2**: DebuggerAgent auto-generates and applies fix patches for FKB-known issues at **95%+ rate** without manual intervention
- **MC1-3**: Auto-regeneration loop triggers when coverage or static analysis falls below thresholds (coverage >= 85%, Critical warnings = 0) — **FR-QGT**

### Progress

- [x] Orchestrator basic routing implemented
- [x] NPE and FKB foundation implemented
- [ ] Gradio and UI component complete separation/integration (~60%)
- [ ] DebuggerAgent auto PR generation logic (~40%)

### Related SRS Requirements

- `FR-ORC`: Task management and routing via Orchestrator
- `FR-QGT`: Quality gate enforcement of test coverage and static analysis
- `FR-ERR`: Error handling with FKB integration

---

## Phase 2: Minimum SaaS Foundation (MVP)

**Goal**: Multi-user cloud environment with authentication, persistent project data, and observability for individual and small team use.

### Milestones

- **Month 4**: GitHub OAuth authentication and session management
- **Month 5**: RDB-based project-scoped execution logs, patches, and test results
- **Month 6**: Real-time agent dashboard (v1) showing thinking process and results

### Definition of Done

- **MC2-1**: GitHub sign-up/in/out with secure session management — **NFR-SEC**
- **MC2-2**: Users can retrieve and replay execution history, patches, and test results per project from DB
- **MC2-3**: Dashboard streams agent communication (task assignment, progress, errors) with <1s latency — **NFR-PRF**

### Progress

- [ ] Authentication and DB schema design (not started)
- [ ] Frontend dashboard mockup (not started)

### Related SRS Requirements

- `FR-ORC`: User-context-aware Orchestrator execution control
- `NFR-SEC`: OAuth authentication, encrypted communication, user data isolation
- `NFR-PRF`: Concurrent database and streaming performance

---

## Phase 3: Enterprise Readiness and Scaling

**Goal**: Production-grade scalability and security with sandboxed multi-tenant execution, RAG-enhanced accuracy, and IDE integration.

### Milestones

- **Month 7**: Docker-based isolated sandbox execution environment
- **Month 8**: Vector DB (Chroma/Qdrant) integration and RAG pipeline
- **Month 9**: VSCode extension rewrite as LSP with beta release

### Definition of Done

- **MC3-1**: All code execution and tests run in isolated Docker containers with zero host/tenant cross-contamination — **NFR-SEC**
- **MC3-2**: RAG-powered context retrieval improves patch relevance by 20% on 100K+ line codebases
- **MC3-3**: VSCode LSP extension provides real-time NexusCore analysis feedback on save and during editing

### Progress

- [ ] Container execution runner prototype (~20%)
- [ ] Vector DB technology selection (~50%)
- [ ] Current VSCode extension (RPC-based) requirements review (~30%)

### Related SRS Requirements

- `FR-LLM`: Dynamic context injection via RAG with token optimization
- `NFR-SEC`: Container isolation, least-privilege enforcement
- `NFR-PRF`: Large codebase indexing and search performance optimization

---

## Delta / Updates

Roadmap covers future plans; for confirmed specifications, refer to SRS/Governance/CR.

- **SRS-driven**: Prioritize CRs to fulfill `docs/srs/NEXUSCORE_SRS.md` FR/NFR requirements
- **Governance-bound**: Freeze boundaries and prohibitions per `docs/governance/NEXUSCORE_GOVERNANCE.md`
- **CR workflow**: New CRs in `docs/spec/` with SRS traceability in fixed format
- **AuthorityLevel**: Minimum requirements fixed in SRS (FR-ORC-003, FR-ORC-004, NFR-SEC-003)

## Revision History

- 2026-04-19: v1.2 Added per-phase milestones, DoD, progress tracking, and SRS requirement mapping
- 2026-04-17: v1.1 Removed [cite:] markers, updated Charter reference, updated FR numbering
- 2025-12-16: v1.0 Initial version
