# Parsing, Resolution, and Graph Contract

## Canonical pipeline

```text
LanguageAdapter → ParsedFile/Universal IR → Resolver
→ optional CFG/DFG → GraphCandidate → CanonicalGraph
```

The current `services/parsing` and `services/code_analysis` paths must converge on this contract. Compatibility adapters may exist temporarily but require deprecation tasks.

Every graph edge carries relation type, origin, extractor, source location, confidence, support level, and index version. Parser/resolver facts support confirmed claims; heuristic/LLM inference is labeled and cannot silently upgrade to confirmed.

The canonical graph is not sent directly to the UI. Bounded projections declare node/edge types, depth, confidence threshold, maximum size, coverage, and truncation reason.
