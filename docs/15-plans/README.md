# Production Delivery Plan

`master-roadmap.md` is the canonical delivery sequence. Each file under `phases/` defines one outcome and its entry/exit evidence. `task-register.md` owns task IDs and dependency edges.

## Dependency rule

A phase may begin discovery early, but implementation cannot bypass prerequisite contracts or data foundations. Technology candidates become plans only after accepted ADRs.

## Completion rule

Task count is not the definition of done. Each phase exits only when its named test/evidence gates pass and the implementation baseline is updated.

`specifications/detailed-product-roadmap.md` retains feature history and detailed product ideas as supporting context. It cannot change phase order, authorize implementation, or override accepted scope. When it conflicts with `master-roadmap.md`, the master roadmap and dependency-aware register control delivery.
