# Copyright (c) 2015 Ansible, Inc.
# All Rights Reserved.

from collections import OrderedDict

# Django REST Framework
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.core.paginator import Paginator as DjangoPaginator
from django.utils.functional import cached_property
from rest_framework import pagination
from rest_framework.response import Response
from rest_framework.utils.urls import replace_query_param
from rest_framework.settings import api_settings
from django.utils.translation import gettext_lazy as _

from ansible_base.rest_filters.rest_framework.field_lookup_backend import (
    FieldLookupBackend,
)
from awx.main.models import ActivityStream, Inventory, InventorySource, Project, UnifiedJobTemplate, WorkflowJobTemplate
from awx.main.utils.common import get_unified_job_summary_epoch
from awx.main.utils.unified_job_summaries import summarized_visible_scope_count, summary_ready_dates


class DisabledPaginator(DjangoPaginator):
    @property
    def num_pages(self):
        return 1

    @property
    def count(self):
        return 200


class ActivityStreamPaginator(DjangoPaginator):
    """Use unfiltered table count for activity stream pagination (AAP-83773)."""

    @cached_property
    def count(self):
        return ActivityStream.objects.count()


class UnifiedJobPaginator(DjangoPaginator):
    """Count visible UnifiedJob rows through a primary-key subquery."""

    def visible_scope_rows(self):
        """Read canonical scope identities from the already-RBAC-filtered queryset."""
        fields = {
            'Job': ('job_template_id', 'organization_id'),
            'ProjectUpdate': ('project_id', 'project__organization_id'),
            'InventoryUpdate': ('inventory_source_id', 'inventory_source__inventory__organization_id'),
            'WorkflowJob': ('unified_job_template_id', 'organization_id'),
            'AdHocCommand': ('inventory_id', 'organization_id'),
            'WorkflowApproval': ('unified_job_node__workflow_job__unified_job_template_id', 'unified_job_node__workflow_job__organization_id'),
            'SystemJob': ('system_job_template_id',),
        }.get(self.object_list.model.__name__)
        if fields is None:
            return None
        return self.object_list.order_by().values(*fields).distinct()

    def epoch_querysets(self, epoch):
        """Split the visible queryset at the migration-backed summary epoch."""
        visible_pks = self.object_list.order_by().values('pk')
        visible = self.object_list.model.objects.filter(pk__in=visible_pks)
        return (
            visible.filter(created__lt=epoch),
            visible.filter(created__gte=epoch),
        )

    @cached_property
    def count(self):
        model_name = getattr(self.object_list.model, '__name__', None)
        if model_name not in {'Job', 'ProjectUpdate', 'InventoryUpdate', 'WorkflowJob', 'AdHocCommand', 'WorkflowApproval', 'SystemJob'}:
            visible_pks = self.object_list.order_by().values('pk')
            return self.object_list.model.objects.filter(pk__in=visible_pks).count()
        epoch = get_unified_job_summary_epoch()
        if epoch is None:
            visible_pks = self.object_list.order_by().values('pk')
            return self.object_list.model.objects.filter(pk__in=visible_pks).count()

        epoch_date = timezone.localtime(epoch).date()
        today = timezone.localdate()
        ready_dates = summary_ready_dates(epoch_date, today)
        scopes = self.visible_scope_rows()
        if scopes is None:
            visible_pks = self.object_list.order_by().values('pk')
            return self.object_list.model.objects.filter(pk__in=visible_pks).count()

        scope_rows = list(scopes)
        fields = {
            'Job': ('job_template_id', 'organization_id'),
            'ProjectUpdate': ('project_id', 'project__organization_id'),
            'InventoryUpdate': ('inventory_source_id', 'inventory_source__inventory__organization_id'),
            'WorkflowJob': ('unified_job_template_id', 'organization_id'),
            'AdHocCommand': ('inventory_id', 'organization_id'),
            'WorkflowApproval': ('unified_job_node__workflow_job__unified_job_template_id', 'unified_job_node__workflow_job__organization_id'),
            'SystemJob': ('system_job_template_id',),
        }[self.object_list.model.__name__]
        resource_ids = [row[fields[0]] for row in scope_rows if row[fields[0]] is not None]
        organization_ids = [row[fields[1]] for row in scope_rows if row[fields[1]] is not None] if len(fields) > 1 else []
        resource_models = {
            'Job': UnifiedJobTemplate,
            'ProjectUpdate': Project,
            'InventoryUpdate': InventorySource,
            'WorkflowJob': WorkflowJobTemplate,
            'AdHocCommand': Inventory,
            'WorkflowApproval': WorkflowJobTemplate,
            'SystemJob': SystemJobTemplate,
        }
        content_type_id = ContentType.objects.get_for_model(resource_models[self.object_list.model.__name__]).id
        summary_total = summarized_visible_scope_count(ready_dates, content_type_id, resource_ids, organization_ids)
        visible_pks = self.object_list.order_by().values('pk')
        live = self.object_list.model.objects.filter(pk__in=visible_pks).exclude(created__date__in=ready_dates).count()
        return summary_total + live


class JobPaginator(DjangoPaginator):
    """Count visible jobs through a primary-key subquery instead of full rows."""

    @cached_property
    def count(self):
        visible_pks = self.object_list.order_by().values("pk")
        return self.object_list.model.objects.filter(pk__in=visible_pks).count()


class Pagination(pagination.PageNumberPagination):
    page_size_query_param = "page_size"
    max_page_size = settings.MAX_PAGE_SIZE
    count_disabled = False

    # FieldLookupBackend reserves these too, but they still filter via a different backend.
    RESERVED_NAMES_THAT_STILL_FILTER = frozenset(
        (
            "search",
            "type",
            "host_filter",
            "user_ansible_id",
            "team_ansible_id",
            "object_ansible_id",
            "assignment",
        )
    )

    def has_filter_params(self, request, view=None):
        non_filtering = set(FieldLookupBackend().reserved_names(view)) - self.RESERVED_NAMES_THAT_STILL_FILTER
        return bool(set(request.query_params) - non_filtering)

    def get_filtered_paginator_class(self):
        # Override when django_paginator_class trades count accuracy for speed --
        # that tradeoff is only safe when there's no filter to make the count wrong.
        return self.django_paginator_class

    def get_next_link(self):
        if not self.page.has_next():
            return None
        url = self.request and self.request.get_full_path() or ""
        url = url.encode("utf-8")
        page_number = self.page.next_page_number()
        return replace_query_param(self.cap_page_size(url), self.page_query_param, page_number)

    def get_previous_link(self):
        if not self.page.has_previous():
            return None
        url = self.request and self.request.get_full_path() or ""
        url = url.encode("utf-8")
        page_number = self.page.previous_page_number()
        return replace_query_param(self.cap_page_size(url), self.page_query_param, page_number)

    def cap_page_size(self, url):
        if int(self.request.query_params.get(self.page_size_query_param, 0)) > self.max_page_size:
            url = replace_query_param(url, self.page_size_query_param, self.max_page_size)
        return url

    def get_html_context(self):
        context = super().get_html_context()
        context["page_links"] = [pl._replace(url=self.cap_page_size(pl.url)) for pl in context["page_links"]]

        return context

    def paginate_queryset(self, queryset, request, **kwargs):
        self.count_disabled = "count_disabled" in request.query_params
        original_paginator = self.django_paginator_class
        try:
            if self.count_disabled:
                self.django_paginator_class = DisabledPaginator
            else:
                filtered_paginator_class = self.get_filtered_paginator_class()
                # Skip the has_filter_params check entirely for classes that don't override
                # get_filtered_paginator_class -- it would be a no-op anyway.
                if filtered_paginator_class is not self.django_paginator_class and self.has_filter_params(request, kwargs.get("view")):
                    self.django_paginator_class = filtered_paginator_class
            return super(Pagination, self).paginate_queryset(queryset, request, **kwargs)
        finally:
            self.django_paginator_class = original_paginator

    def get_paginated_response(self, data):
        if self.count_disabled:
            return Response({"results": data})
        return super(Pagination, self).get_paginated_response(data)


class ActivityStreamPagination(Pagination):
    django_paginator_class = ActivityStreamPaginator

    def get_filtered_paginator_class(self):
        return DjangoPaginator


class UnifiedJobPagination(Pagination):
    django_paginator_class = UnifiedJobPaginator

    def get_filtered_paginator_class(self):
        return DjangoPaginator


class JobPagination(Pagination):
    django_paginator_class = JobPaginator


class LimitPagination(pagination.BasePagination):
    default_limit = api_settings.PAGE_SIZE
    limit_query_param = "limit"
    limit_query_description = _("Number of results to return per page.")
    max_page_size = settings.MAX_PAGE_SIZE

    def paginate_queryset(self, queryset, request, view=None):
        self.limit = self.get_limit(request)
        self.request = request

        return list(queryset[0 : self.limit])

    def get_paginated_response(self, data):
        return Response(OrderedDict([("results", data)]))

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "properties": {
                "results": schema,
            },
        }

    def get_limit(self, request):
        try:
            return pagination._positive_int(request.query_params[self.limit_query_param], strict=True)
        except (KeyError, ValueError):
            pass

        return self.default_limit


class UnifiedJobEventPagination(Pagination):
    """
    By default, use Pagination for all operations.
    If `limit` query parameter specified use LimitPagination
    """

    def __init__(self, *args, **kwargs):
        self.use_limit_paginator = False
        self.limit_pagination = LimitPagination()
        super().__init__(*args, **kwargs)

    def paginate_queryset(self, queryset, request, view=None):
        if "limit" in request.query_params:
            self.use_limit_paginator = True

        if self.use_limit_paginator:
            return self.limit_pagination.paginate_queryset(queryset, request, view=view)
        return super().paginate_queryset(queryset, request, view=view)

    def get_paginated_response(self, data):
        if self.use_limit_paginator:
            return self.limit_pagination.get_paginated_response(data)
        return super().get_paginated_response(data)

    def get_paginated_response_schema(self, schema):
        if self.use_limit_paginator:
            return self.limit_pagination.get_paginated_response_schema(schema)
        return super().get_paginated_response_schema(schema)
