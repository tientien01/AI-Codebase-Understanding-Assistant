# Technology Radar

| Technology | Status | Evaluation trigger |
| --- | --- | --- |
| FastAPI, React, PostgreSQL, Alembic, Docker | Adopt | Production foundation |
| Dramatiq 2.2.0 | Adopt | JOB-002 passed 15/15 recovery/cancellation PoC runs; integrate in JOB-003 |
| RQ 2.10.0 | Hold | JOB-002 forced-worker-loss recovery failed 3/3 runs within 30 seconds |
| pgvector | Trial later | Semantic recall below accepted threshold |
| Qdrant | Hold | Vector workload exceeds PostgreSQL capacity |
| Neo4j/FalkorDB | Hold | Validated multi-hop query bottleneck |
| OpenSearch | Hold | PostgreSQL/search artifacts miss scale or latency targets |
| LangGraph | Hold | Workflow needs durable checkpoint/human pause beyond current state machine |
| Kubernetes | Hold | Multi-node scaling and operational team requirement |
| ELK.js/Graphology | Assess | Dagre/projection benchmark fails UX targets |
| Monaco | Hold | Editing/IDE behavior becomes an accepted product requirement |

Candidates under Assess/Trial/Hold cannot enter production code without an accepted ADR and authorized task.
