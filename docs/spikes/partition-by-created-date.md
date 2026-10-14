# Spike: Partition AWX execution tables by UnifiedJob.created (UTC)

## Summary

This spike proposes partitioning the AWX execution tables by the UTC date of the execution row’s `created` timestamp, rather than by start time. The partition key is the UTC date of `UnifiedJob.created`, which is stable for the lifetime of a job record and is available immediately when the job record is created.

This is a safer and simpler design than partitioning by start time because:
- `created` is immutable
- it is known at insert time
- jobs can be queued, delayed, or start much later than they were created
- partition routing does not depend on job runtime timing

This plan also includes a clear rule for API list behavior: when a list request is doing searching or sorting, the request must include a created-date range filter.

## Objective

Partition the AWX execution tables by the UTC date of `UnifiedJob.created` to improve the performance of historical queries and large execution lists, while preserving:
- AWX’s current permission model
- list API behavior
- correctness for filtered, sorted, and paginated execution views

## AWX execution model context

The AWX execution model is structured around a common base class:

- `UnifiedJob`
- derived concrete execution models such as:
  - `Job`
  - `ProjectUpdate`
  - `InventoryUpdate`
  - workflow execution records
  - related execution subtypes

The API-facing job list is implemented from the execution family, not from a standalone “job start” table. The partitioning strategy therefore needs to work at the shared execution level and remain compatible with the inheritance model already used by AWX.

The repository confirms:
- `Job` is defined in `awx/main/models/jobs.py`
- `ProjectUpdate` is defined in `awx/main/models/projects.py`
- the job list endpoint is defined under `awx/api/urls/job.py`
- generic list views use the shared AWX list infrastructure in `awx/api/generics.py`

## Partitioning design

### Partition key

Use:
- `date(created AT TIME ZONE 'UTC')`

Examples:
- `created = 2026-10-14T22:45:00Z` => partition date `2026-10-14`
- `created = 2026-10-15T00:10:00Z` => partition date `2026-10-15`

This is the partition key for routing a new execution row to its date-partition.

### Why created, not start time

Partitioning by start time is operationally awkward because:
- jobs may be created long before they actually start
- there is no reliable, always-available start time for all job types
- queued jobs may move across day boundaries
- runtime timing drift makes the partition assignment unstable or harder to reason about

By contrast, `created` is:
- present on every execution row
- stable after insertion
- available immediately
- a better fit for insert-time partition routing

### Routing logic

New execution rows are inserted into the partition corresponding to their created date in UTC, and remain there for the rest of their lifetime.

This means:
- no row movement
- no re-partitioning later
- clear and stable historical grouping

## Daily summary model

A persistent internal summary model should track partition-level totals by UTC created date.

### Goals

This summary should support historical aggregate queries without exposing a new API contract or changing permission semantics.

### Recommended summary record shape

One row per UTC date:

- `partition_date` (date, unique)
- `generated_at` (timestamp)
- `summarized` (boolean)
- aggregate counts, for example:
  - total_jobs
  - total_project_updates
  - total_inventory_updates
  - total_success
  - total_failed
  - total_error
  - total_canceled
  - counts by job type
  - counts by template or related dimension when needed
- optionally, summary rows for nested dimensions if those are required by the existing aggregate behavior

The exact schema can be expanded later, but the core requirement is:
- one internal summary row per created-date partition
- safe idempotent generation
- no API exposure

### Summary readiness

A partition is summary-ready only when all execution rows assigned to that created date are terminal.

That means:
- pending, waiting, or running rows for that partition block summary generation
- once all rows are terminal, the summary can be built
- generation must be idempotent and retry-safe

### Fallback behavior

If a summary is missing, incomplete, or not ready:
- do not use partial summary values
- fallback to the underlying execution table query

This is critical because summary data must never become a separate source of truth.

## API behavior and date filters

The default listing experience should remain unchanged:
- newest-first default list
- no forced date range for plain default listing

However, when a list request is performing a search or sorting operation on execution resources, the request should be required to include a created-date range filter.

### Required rule

If the request is:
- searching
- sorting
- ordering
- filtering heavily on execution list endpoints

then require:
- `created__gte`
- `created__lt`

or an equivalent accepted pair such as:
- `created_after`
- `created_before`

The rule should be enforced in the shared list layer so it applies to all execution-related list views.

### Recommended interval

Use a half-open UTC interval:
- `created >= start`
- `created < end`

Examples:
- `created__gte=2026-10-01T00:00:00Z`
- `created__lt=2026-10-02T00:00:00Z`

This avoids midnight boundary ambiguity and matches stable partition boundaries.

### Why enforce only on search/sort

This keeps the default UX friendly:
- simple browsing can remain easy
- expensive or large execution queries are forced to use a bounded time window
- query cost is predictable
- partition pruning is much more effective

This is the key operational rule of the spike:
- plain list view: okay without explicit range
- search or sort on execution resources: require created-date filter

## Correctness and permission model

The summary optimization must never bypass AWX access controls.

### Rules

- Summary rows are internal and not exposed in the API
- summaries can only be used for eligible historical partitions
- permission-aware queries must still use the same user-scoping rules as the underlying queryset
- if a summary cannot safely answer the query, fallback to the underlying tables
- if a summary is missing or not ready, do not partially answer the query

This ensures the summary is an optimization, not a second source of truth.

## Execution code and query integration

The implementation plan should target the shared execution query layer and not just individual serializers.

### Candidate integration points

- `awx/api/generics.py`
- list endpoints for execution types built on `ListAPIView` / `SubListAPIView`
- any shared filter logic used by job-like resources

### Expected behavior

For execution models:
- `search`, `sort`, or `order` without created range should return an error
- `search`, `sort`, or `order` with created range should proceed
- default list view without search/sort should continue to work

## Test plan

### Partition routing

- jobs created before midnight UTC
- jobs created after midnight UTC
- jobs delayed or started much later than creation time
- jobs with different execution subtypes
- jobs created on same day but different state transitions

### Summary correctness

- summary is generated only after all rows in a created-date partition are terminal
- generation is idempotent
- retry of summary generation does not double-count
- missing summary causes fallback to base query
- partial or stale summary values are never used

### API correctness

- default list view works without a created filter
- search/sort requests without a created range fail with a clear error
- search/sort requests with proper created range succeed
- permission-scoped results remain identical to the underlying queryset
- pagination remains stable across partitions

### Query performance validation

- benchmark default list vs date-bounded list
- benchmark search/sort queries before and after partitioning
- confirm partition pruning on date-bounded queries
- confirm large execution queries are bounded by the created window

## Risks and tradeoffs

### Benefits

- stable partition assignment
- simpler insert logic
- better historical query pruning
- easier summary generation
- better operational behavior for jobs queued or delayed

### Costs

- created-date partitioning does not reflect actual runtime window
- jobs delayed far past creation time may still remain in the created-date partition
- historical summary readiness depends on all jobs created on that date being terminal

These are acceptable tradeoffs for this spike, especially because `created` is a stable and precise insert-time boundary.

## Recommended implementation direction

Use:
- `UnifiedJob.created` in UTC as the partition key
- created-date partition summary tables for historical aggregate acceleration
- created-date enforcement for search/sort-heavy execution list requests
- summary fallback to underlying tables wherever correctness is uncertain

This is the safest and simplest strategy for AWX and aligns with the existing execution model.

## Deliverables

The spike should produce:

- model and query assessment of the execution hierarchy
- partitioning prototype for execution rows keyed by `UnifiedJob.created` UTC date
- summary model design
- summary generation and fallback logic
- API enforcement rule for search/sort requiring created-date range
- tests for routing, summary correctness, and permission safety
- performance validation of date-bounded queries

## Final recommendation

Proceed with partitioning by `UnifiedJob.created` in UTC, and enforce a created-date range whenever execution list requests are searching or sorting. This keeps the system simple, stable, and aligned with AWX’s actual execution model while reducing the risk of expensive unbounded scans.
