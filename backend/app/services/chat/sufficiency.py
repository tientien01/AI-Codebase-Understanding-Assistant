from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from app.services.evidence.selection import EvidenceContext
from app.services.retrieval.contracts import SupportType
from app.services.retrieval.ranking import RankedCandidate, SUPPORT_ORDER


class SufficiencyAction(str, Enum):
    ANSWER = "answer"
    REPAIR = "repair"
    INSUFFICIENT = "insufficient"


@dataclass(frozen=True)
class SufficiencyDecision:
    action: SufficiencyAction
    reason_code: str
    missing_requirements: tuple[str, ...]
    coverage: tuple[str, ...]
    repair_query: str | None = None


class SufficiencyPolicy:
    """Question-specific deterministic support policy over selected evidence."""

    def evaluate(
        self,
        question_type: str,
        question: str,
        context: EvidenceContext,
        *,
        allow_repair: bool,
    ) -> SufficiencyDecision:
        strong = [
            block
            for block in context.selected
            if block.support_type in {SupportType.SOURCE_EXACT, SupportType.STATIC_RESOLVED}
        ]
        distinct_sources = {block.file_path for block in strong}
        retrievers = {name for block in strong for name in block.retrievers}
        coverage = tuple(sorted({f"source:{path}" for path in distinct_sources} | {f"retriever:{name}" for name in retrievers}))
        missing: list[str] = []
        if question_type in {"flow_tracing", "api_question", "impact_analysis"}:
            if len(strong) < 2:
                missing.append("required_strong_evidence_count:2")
            required_retriever = "endpoint" if question_type == "api_question" else "graph"
            if required_retriever not in retrievers:
                missing.append(f"required_retriever:{required_retriever}")
        elif question_type in {"architecture_overview", "onboarding"}:
            if len(distinct_sources) < 2:
                missing.append("required_distinct_sources:2")
        elif not strong:
            missing.append("required_strong_evidence_count:1")

        if not missing:
            return SufficiencyDecision(SufficiencyAction.ANSWER, "requirements_satisfied", (), coverage)
        repairable_types = {
            "flow_tracing",
            "api_question",
            "impact_analysis",
            "architecture_overview",
            "onboarding",
        }
        if allow_repair and question_type in repairable_types:
            return SufficiencyDecision(
                SufficiencyAction.REPAIR,
                "repairable_undercoverage",
                tuple(missing),
                coverage,
                self.repair_query(question_type, question),
            )
        return SufficiencyDecision(
            SufficiencyAction.INSUFFICIENT,
            "requirements_unsatisfied",
            tuple(missing),
            coverage,
        )

    @staticmethod
    def repair_query(question_type: str, question: str) -> str:
        suffixes = {
            "flow_tracing": "endpoint handler caller callee graph relation",
            "api_question": "endpoint handler route source",
            "impact_analysis": "dependency reference caller callee graph relation",
            "architecture_overview": "readme entrypoint configuration module architecture",
            "onboarding": "readme documentation entrypoint setup module",
        }
        suffix = suffixes.get(question_type, "source definition reference")
        return f"{question.strip()} {suffix}"


def merge_ranked_candidates(
    first: tuple[RankedCandidate, ...],
    second: tuple[RankedCandidate, ...],
) -> tuple[RankedCandidate, ...]:
    groups: dict[tuple[str, str, int, int], list[RankedCandidate]] = {}
    for item in (*first, *second):
        candidate = item.candidate
        key = (
            candidate.entity_key,
            candidate.source_key,
            candidate.chunk.start_line,
            candidate.chunk.end_line,
        )
        groups.setdefault(key, []).append(item)
    merged: list[RankedCandidate] = []
    for key in sorted(groups):
        items = groups[key]
        config_ids = {item.ranking_config_id for item in items}
        owners = {(item.candidate.repository_id, item.candidate.index_version_id) for item in items}
        if len(config_ids) != 1 or len(owners) != 1:
            raise ValueError("repair candidates cross ranking or ownership boundary")
        best = min(
            items,
            key=lambda item: (
                -item.fused_score,
                SUPPORT_ORDER[item.support_type],
                item.best_rank,
                item.candidate.candidate_id,
            ),
        )
        merged.append(
            replace(
                best,
                candidate_ids=tuple(sorted({value for item in items for value in item.candidate_ids})),
                retrievers=tuple(sorted({value for item in items for value in item.retrievers}, key=lambda value: value.value)),
                matched_terms=tuple(sorted({value for item in items for value in item.matched_terms})),
                reason_codes=tuple(sorted({value for item in items for value in item.reason_codes})),
                provenance_refs=tuple(sorted({value for item in items for value in item.provenance_refs})),
            )
        )
    return tuple(
        sorted(
            merged,
            key=lambda item: (-item.fused_score, SUPPORT_ORDER[item.support_type], item.best_rank, item.candidate.entity_key),
        )
    )
