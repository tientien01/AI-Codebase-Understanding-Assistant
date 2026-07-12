# Release Checklist

Status: Accepted L3 checklist  
Release:  
Candidate digest:  
Evidence manifest:  
Reviewer/date:

Use this checklist only with a completed manifest created from `release-manifest-template.md`. Every checked item must link to evidence for the same release candidate and configuration profile.

- [ ] No open P0 production gap or critical known defect.
- [ ] Database install/upgrade and schema drift pass.
- [ ] Worker restart, retry, cancellation, stale recovery, and atomic activation pass.
- [ ] Full/incremental equivalence passes on reference fixtures.
- [ ] Import security, secret, auth, rate/size, dependency and container scans pass.
- [ ] API contract, backend integration, frontend build/component/E2E pass.
- [ ] Retrieval, graph, citation, hallucination, insufficient-evidence, latency and cost thresholds pass.
- [ ] Liveness/readiness, dashboards, alerts and runbooks are verified.
- [ ] Backup/restore and rollback drills pass.
- [ ] Production-like deployment smoke passes using release artifacts.
- [ ] Baseline, changelog, version, operations and user docs are current.
