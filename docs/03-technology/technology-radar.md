# Technology Radar

| Technology | Status | Evaluation trigger |
| --- | --- | --- |
| FastAPI, React, PostgreSQL, Alembic, Docker | Adopt | Production foundation |
| RQ vs Dramatiq | Assess | Durable job PoC measuring recovery/cancellation |
| pgvector | Trial later | Semantic recall below accepted threshold |
| Qdrant | Hold | Vector workload exceeds PostgreSQL capacity |
| Neo4j/FalkorDB | Hold | Validated multi-hop query bottleneck |
| OpenSearch | Hold | PostgreSQL/search artifacts miss scale or latency targets |
| LangGraph | Hold | Workflow needs durable checkpoint/human pause beyond current state machine |
| Kubernetes | Hold | Multi-node scaling and operational team requirement |
| ELK.js/Graphology | Assess | Dagre/projection benchmark fails UX targets |
| Monaco | Hold | Editing/IDE behavior becomes an accepted product requirement |

Candidates under Assess/Trial/Hold cannot enter production code without an accepted ADR and authorized task.
