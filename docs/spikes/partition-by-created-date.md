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

Every concrete child table must be partitioned too. Partitioning only `main_unifiedjob` leaves child-table scans, joins, and foreign-key lookups unpruned. Each child partition must use the same UTC `UnifiedJob.created` boundary as its parent row, with matching partition names and bounds.

The API-facing job list is implemented from the execution family, not from a standalone “job start” table. The partitioning strategy therefore needs to work across the shared parent and every concrete child table while remaining compatible with AWX multi-table inheritance.

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

New execution rows are inserted into the parent partition corresponding to their created date in UTC. The matching child row must be inserted into the same-date child partition and remain there for the rest of its lifetime.

This means:
- no row movement
- no re-partitioning later
- parent and child rows remain co-located by date
- joins between `main_unifiedjob` and child tables can prune to the same partition set

The migration must cover every concrete `UnifiedJob` descendant, including `Job`, `ProjectUpdate`, `InventoryUpdate`, `WorkflowJob`, `AdHocCommand`, and system execution models where applicable. New descendants must fail migration checks until a matching partition strategy exists.

## Daily summary model

A persistent internal summary model should track partition-level totals by UTC created date.

### Goals

This summary should support historical aggregate queries without exposing a new API contract or changing permission semantics.

### Recommended summary record shape

Summary rows are keyed by UTC date plus permission-relevant resource scope:

- `partition_date`
- `content_type_id`: Django content type ID for the permission-bearing resource
- `object_id`: resource primary key

For the global aggregate, both `content_type_id` and `object_id` are NULL. This matches AWX RBAC terminology and its `(content_type_id, object_id)` resource identity.
- `generated_at`
- `summarized`
- `total`
- `status_totals`
- `meta`

A global row supports unrestricted aggregates. Scoped rows let views apply existing permission querysets before consuming summaries. Permissions are not inferred from summary data: jobs resolve to their related job template, project updates to project, inventory updates to inventory source, and workflow jobs to workflow job template. The view intersects permitted resource IDs with scoped summary rows, then combines global/scoped results only when semantics are equivalent.

The exact aggregate dimensions can expand later, but every dimension used by an API response must have an explicit scope and correctness rule. No summary row is exposed directly through the API.

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

## Implementation sketch: force a created-date range for execution search/sort

This spike proposes enforcing a created-date range for execution-resource list requests doing search or expensive filtering. The default list, ordinary pagination, and default ordering remain unchanged until query measurements justify stricter enforcement.

The enforcement should live in the shared AWX list base used by execution models.

Example implementation:

```python
class ListAPIView(generics.ListAPIView, GenericAPIView):
    def _has_created_date_range(self):
        qp = self.request.query_params
        key_pairs = [
            ('created__gte', 'created__lt'),
            ('created_after', 'created_before'),
        ]
        for start_key, end_key in key_pairs:
            if start_key in qp and end_key in qp:
                return True
        return False

    def _require_created_date_for_unified_job_search_sort(self):
        if not getattr(self, 'model', None):
            return
        try:
            is_unified_job = issubclass(self.model, UnifiedJob)
        except TypeError:
            return
        if not is_unified_job:
            return

        qp = self.request.query_params
        has_search_or_expensive_filter = any(k in qp for k in ('search', 'related__search', 'or__', 'id__in', 'created__')) or any(
            k in qp for k in ('order_by', 'ordering', 'sort')
        )
        if not has_search_or_expensive_filter:
            return

        if self._has_created_date_range():
            return

        raise ParseError(
            _('Search/sort requests for execution resources require a created date range filter. '
              'Include created__gte and created__lt (UTC) or created_after and created_before.')
        )

    def get_queryset(self):
        self._require_created_date_for_unified_job_search_sort()
        return self.request.user.get_queryset(self.model)
```

Why this matches the spike:
- it limits expensive searches and sorts to bounded created-date windows
- it applies only to execution-resource list views
- it preserves default list behavior when no search/sort is happening
- it keeps `created` as the canonical partition key and date filter

Example tests:

```python
def test_unified_job_list_requires_created_date_with_order_by(mocker):
    request = mocker.Mock()
    request.query_params = {'order_by': '-created'}
    view = ListAPIView()
    view.model = UnifiedJob
    view.request = request

    with pytest.raises(ParseError):
        view.get_queryset()
```

```python
def test_unified_job_list_requires_created_date_with_search(mocker):
    request = mocker.Mock()
    request.query_params = {'search': 'foo'}
    view = ListAPIView()
    view.model = UnifiedJob
    view.request = request

    with pytest.raises(ParseError):
        view.get_queryset()
```

```python
def test_unified_job_list_allows_created_date_range(mocker):
    request = mocker.Mock()
    request.query_params = {
        'order_by': '-created',
        'created__gte': '2026-01-01T00:00:00Z',
        'created__lt': '2026-01-02T00:00:00Z',
    }
    view = ListAPIView()
    view.model = UnifiedJob
    view.request = request
    view.request.user = mocker.Mock()
    view.request.user.get_queryset.return_value = object()

    assert view.get_queryset() is not None
```

## Implementation order: correctness before partitioning

Physical partitioning is deferred until date-bounded query behavior, scoped summaries, cleanup, and permission correctness pass in local Docker Compose and staging. Existing UnifiedJob and concrete child tables are not partitioned today.

The implementation proceeds in four reversible stages:

1. date-range enforcement and query instrumentation;
2. scoped summary generation and validation;
3. view consumption plus cleanup integration;
4. physical partitioning of `UnifiedJob` and every concrete child table.

Stages 1–3 must work against the current unpartitioned tables. They provide a correctness baseline and can be rolled back without table migration.

### Stage 1: date-range enforcement

Apply the rule only to UnifiedJob-derived list views when an explicit search or expensive filter is present. Require a half-open UTC range:

```text
created__gte=<UTC start>&created__lt=<UTC end>
```

Keep the default unfiltered list unchanged. Do not reject ordinary pagination or default ordering until query measurements justify that behavior. Return a clear `400` error for unbounded search/filter requests.

Record query duration, selected view, user scope, date range, and whether summary or base-table execution was used. Do not log credentials or full query parameters.

### Stage 2: scoped summary generation

Generate summaries on current unpartitioned tables first. Summary generation runs as a queued `@task`, not inline in job completion or API requests. It has three triggers:

- a post-terminal-job hook enqueues the job’s `created` date;
- the periodic scheduler retries recent dirty/not-ready dates;
- cleanup marks affected dates dirty and enqueues regeneration.

The task accepts one date or a date range, takes an advisory lock per date, and is idempotent. The post-terminal hook only enqueues work.

For each date:

- acquire the date lock;
- recheck that no UnifiedJob row for the date remains non-terminal;
- reject or mark not-ready when any row is non-terminal;
- resolve each execution to its permission owner;
- write global and resource-scoped rows;
- replace rows atomically only after all counts complete;
- mark dates dirty when late rows, corrections, or cleanup affect them;
- support explicit rebuild and delete for testing.

Resource ownership:

```text
Job              -> unified_job_template
ProjectUpdate    -> project
InventoryUpdate  -> inventory_source
WorkflowJob      -> workflow_job_template
```

Summary rows are never authoritative. Missing, dirty, incomplete, or permission-incompatible summaries fall back to base tables.

### Stage 3: view and cleanup integration

Views and paginator count paths resolve the caller’s existing access queryset first, then consume only matching scoped summary rows. A summary-backed count must combine:

1. finalized, summarized date partitions from scoped summary rows;
2. unsummarized or not-yet-terminal date partitions from the live RBAC queryset.

The live portion must use the same RBAC visibility semantics as the endpoint. Never count all summary rows and then apply permissions afterward.

Resource ownership scopes cover direct resource permissions. Summary rows use the `ContentType` of the permission-bearing resource, not the execution subtype:

```text
Job              -> UnifiedJobTemplate
ProjectUpdate    -> Project
InventoryUpdate  -> InventorySource
WorkflowJob      -> WorkflowJobTemplate
```

The resulting summary identity is `(content_type_id, object_id)`, matching RBAC `RoleEvaluation` and `Role` records.

Organization-level, inventory-level, team-derived, and other access paths can overlap these scopes. The implementation must either add matching scope rows and deduplicate by execution ID, or fall back to the live RBAC count for that request. Summing overlapping scopes without deduplication is invalid.

Global summaries are valid only for unrestricted callers and aggregates whose semantics match exactly. Row-level API results continue using base tables until partitioning validation is complete.

Update Activity/UnifiedJob cleanup to:

1. delete expired execution rows and dependent child rows;
2. mark affected summary dates dirty;
3. remove or rebuild affected summary scopes;
4. never leave a stale row marked `summarized=True`.

Paginator correctness tests must compare summary-backed counts and base-table RBAC counts for superuser, system auditor, org admin, and org member users across all resource ownership and organization/team permission paths. Test dates with terminal rows, active rows, missing summaries, stale summaries, cleanup, overlapping scopes, and late inserts.

### Stage 4: physical partitioning

Only after stages 1–3 pass at target scale, partition `UnifiedJob` and every concrete child table using matching UTC `created` bounds. Parent and child rows must be co-located by date. Validate constraints, foreign keys, polymorphic joins, cleanup, rollback, and partition pruning before production migration.

## Real partitioning and summary generation plan

This spike should be implemented in four stages above, with summary-first rollout followed by table partitioning.

### Stage 1: persistent per-day summary table

Add a summary table keyed by `partition_date` (UTC date from `UnifiedJob.created`). This summary is internal and does not change API shape.

Recommended model:

```python
class UnifiedJobCreatedDateSummary(models.Model):
    partition_date = models.DateField(primary_key=True)
    generated_at = models.DateTimeField(null=True, blank=True)
    summarized = models.BooleanField(default=False)
    totals = models.JSONField(default=dict)
    template_totals = models.JSONField(default=dict)
    org_totals = models.JSONField(default=dict)
    meta = models.JSONField(default=dict)

    class Meta:
        db_table = 'main_unifiedjob_created_date_summary'
```

A generation task should:
- accept a date or a date range;
- use an advisory lock to prevent duplicate generation;
- recheck readiness inside the lock;
- ensure all rows for that created-date partition are terminal before summarizing;
- resolve each execution to permission-relevant scope IDs;
- compute global and scoped status/count summaries;
- upsert rows atomically with `summarized=True`;
- mark affected rows dirty after late inserts or cleanup;
- skip not-ready partitions and retry later.

Pseudo-code:

```python
TERMINAL_STATUSES = ('successful', 'failed', 'error', 'canceled')


def generate_summary_for_date(partition_date):
    qs = UnifiedJob.objects.extra(
        where=["(created AT TIME ZONE 'UTC')::date = %s"],
        params=[partition_date],
    )
    if qs.exclude(status__in=TERMINAL_STATUSES).exists():
        return False

    status_counts = dict(qs.values('status').annotate(c=Count('id')).values_list('status', 'c'))

    UnifiedJobCreatedDateSummary.objects.update_or_create(
        partition_date=partition_date,
        content_type_id=None,
        object_id=None,
        defaults={
            'generated_at': timezone.now(),
            'summarized': True,
            'total': qs.count(),
            'status_totals': status_counts,
        },
    )

    # Generate additional scoped rows from each subtype's permission owner.
    # Job -> unified_job_template; ProjectUpdate -> project;
    # InventoryUpdate -> inventory_source; WorkflowJob -> workflow_job_template.
    # Each scope is queried through the same access queryset used by its view;
    # never use a global row to answer a scoped request.
    return True
```

This allows aggregate queries to use per-day summary rows as an optimization without making the summary a second source of truth.

### Stage 2: table partitioning by created-date

After the summary model is tested and stable, the underlying execution table can be converted to a partitioned table by the UTC created date.

Example SQL pattern for Postgres:

```sql
ALTER TABLE main_unifiedjob ADD COLUMN created_date date
  GENERATED ALWAYS AS ((created AT TIME ZONE 'UTC')::date) STORED;

ALTER TABLE main_unifiedjob PARTITION BY RANGE (created_date);

CREATE TABLE main_unifiedjob_2026_10_14 PARTITION OF main_unifiedjob
  FOR VALUES FROM ('2026-10-14') TO ('2026-10-15');
```

Practical notes:
- This is a larger migration with more risk than the summary table alone.
- For existing huge tables, use staging validation and a table-swap migration strategy if direct ALTER is not feasible.
- Ensure indexes, constraints, and triggers are recreated on every parent and child partition.
- Preserve parent/child one-to-one links and validate that both rows always land in the same date partition.
- Validate polymorphic content-type queries and every child-table join with `EXPLAIN`.
- PostgreSQL partitioned-table primary keys and unique constraints must include the partition key; this may require redesigning existing `id`-only constraints and foreign keys.
- Foreign keys between partitioned parent/child tables need explicit PostgreSQL-version validation; if unsupported for the required inheritance layout, use controlled application routing and migration checks rather than weakening referential integrity.

### Operational scheduling

The summary generation should be scheduled as a periodic background task, for example:
- nightly summary generation for the previous day
- hourly recheck for the current partition while jobs are still active
- backfill job for historical partitions

This task should:
- skip any date with any non-terminal jobs;
- generate summary only for finalized dates;
- be idempotent and safe under retry;
- use an advisory DB lock to prevent duplicate runs;
- tolerate jobs finishing after their created date;
- be enqueued by terminal-job completion, periodic retry, and cleanup.

This is the concrete execution plan behind the spike: summary table first, then real DB partitioning after the summary model and API behavior are proven.

## Final note

The most important design rule is that the summary is an optimization, not the canonical truth. If a partition is not finalized or a required permission dimension is not covered by the summary, the system must fall back to the base execution table. The created-date partitioning and summary models are valuable only when they preserve correctness and do not change access semantics.
