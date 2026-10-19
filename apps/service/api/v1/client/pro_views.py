from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from apps.service import pro
from apps.service.attributes import request_language, translated
from apps.service.paginations.get_pro import get_pro_paginator
from exceptions.error_exception import CustomApiException
from exceptions.error_messages import ErrorCodes
from .pro_serializers import (
    ProjectSerializer, ProjectListQuerySerializer, LinkItemsSerializer, UnlinkItemsSerializer, PeriodSerializer,
    PeriodPageSerializer, LinkResultSerializer, UnlinkedOrderSerializer, DashboardSerializer,
    ProjectSummarySerializer, ProjectItemSerializer,
)

TAGS = ["PRO"]
FORBIDDEN_NOTE = " Not a PRO customer → 403 (`error_code` 34)."

PERIOD_PARAMETERS = [
    OpenApiParameter(name="from", location=OpenApiParameter.QUERY, type=OpenApiTypes.DATE,
                     description="Order date from (inclusive)"),
    OpenApiParameter(name="to", location=OpenApiParameter.QUERY, type=OpenApiTypes.DATE,
                     description="Order date to (inclusive)"),
]
PAGE_PARAMETERS = [
    OpenApiParameter(name="page", location=OpenApiParameter.QUERY, type=OpenApiTypes.INT),
    OpenApiParameter(name="page_size", location=OpenApiParameter.QUERY, type=OpenApiTypes.INT,
                     description="Default 20, max 100"),
]


def validated(serializer_class, data):
    serializer = serializer_class(data=data)
    if not serializer.is_valid():
        raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)
    return serializer.validated_data


def ok(result, code=status.HTTP_200_OK):
    return Response(data={"result": result, "ok": True}, status=code)


def category_name(request):
    language = request_language(request)
    return lambda category: translated(category, "name", language)


class ProViewSet(ViewSet):
    """PRO customer's projects and their expenses (apps/service/pro.py)."""

    def _project(self, request, pk, customer=None):
        customer = customer or pro.pro_customer(request)
        return pro.get_project(customer, pk)

    def _project_data(self, project):
        project = pro.projects_with_counts(project.customer).get(pk=project.pk)
        return ProjectSerializer(project).data

    @extend_schema(
        summary="PRO projects",
        description="Customer's projects, newest first; `?status=active|archived`." + FORBIDDEN_NOTE,
        parameters=[OpenApiParameter(name="status", location=OpenApiParameter.QUERY, type=OpenApiTypes.STR,
                                     enum=["active", "archived"])],
        responses={200: ProjectSerializer(many=True)},
        tags=TAGS,
    )
    def project_list(self, request):
        customer = pro.pro_customer(request)
        params = validated(ProjectListQuerySerializer, request.query_params)
        projects = pro.projects_with_counts(customer)
        if params.get("status"):
            projects = projects.filter(status=params["status"])
        return ok(ProjectSerializer(projects, many=True).data)

    @extend_schema(
        summary="Create PRO project",
        description="`name` 3-100 characters, unique among the customer's active projects (case-insensitive, "
                    "`error_code` 35)." + FORBIDDEN_NOTE,
        request=ProjectSerializer,
        responses={201: ProjectSerializer},
        tags=TAGS,
    )
    def project_create(self, request):
        customer = pro.pro_customer(request)
        data = validated(ProjectSerializer, request.data)
        project = pro.save_project(pro.Project(customer=customer, **data))
        return ok(self._project_data(project), status.HTTP_201_CREATED)

    @extend_schema(
        summary="PRO project detail",
        description="Another customer's project → 404." + FORBIDDEN_NOTE,
        responses={200: ProjectSerializer},
        tags=TAGS,
    )
    def project_detail(self, request, pk):
        return ok(self._project_data(self._project(request, pk)))

    @extend_schema(
        summary="Update PRO project",
        description="Partial update of `name`, `address`, `comment`." + FORBIDDEN_NOTE,
        request=ProjectSerializer,
        responses={200: ProjectSerializer},
        tags=TAGS,
    )
    def project_update(self, request, pk):
        project = self._project(request, pk)
        serializer = ProjectSerializer(project, data=request.data, partial=True)
        if not serializer.is_valid():
            raise CustomApiException(error_code=ErrorCodes.VALIDATION_FAILED, message=serializer.errors)
        for field, value in serializer.validated_data.items():
            setattr(project, field, value)
        pro.save_project(project)
        return ok(self._project_data(project))

    @extend_schema(
        summary="Delete PRO project",
        description="Only a project without linked order items; with items → 409 (`error_code` 36), "
                    "archive it instead." + FORBIDDEN_NOTE,
        responses={204: OpenApiResponse(description="Project deleted")},
        tags=TAGS,
    )
    def project_delete(self, request, pk):
        pro.delete_project(self._project(request, pk))
        return ok("Project deleted", status.HTTP_204_NO_CONTENT)

    @extend_schema(
        summary="Archive PRO project",
        description="Items stay linked and keep counting; no new items can be linked to it." + FORBIDDEN_NOTE,
        request=None,
        responses={200: ProjectSerializer},
        tags=TAGS,
    )
    def project_archive(self, request, pk):
        return ok(self._project_data(pro.archive_project(self._project(request, pk))))

    @extend_schema(
        summary="Restore PRO project",
        description="Back to active; an active project with the same name → 400 (`error_code` 35)." + FORBIDDEN_NOTE,
        request=None,
        responses={200: ProjectSerializer},
        tags=TAGS,
    )
    def project_restore(self, request, pk):
        return ok(self._project_data(pro.restore_project(self._project(request, pk))))

    @extend_schema(
        summary="PRO project summary",
        description="Expenses of the project: paid, not canceled orders, by the order date. Goods = price after the "
                    "product discount × quantity less the item's share of the promocode discount; delivery = the "
                    "item's share of the order's delivery (both split by the item sums)." + FORBIDDEN_NOTE,
        parameters=PERIOD_PARAMETERS,
        responses={200: ProjectSummarySerializer},
        tags=TAGS,
    )
    def project_summary(self, request, pk):
        customer = pro.pro_customer(request)
        project = self._project(request, pk, customer)
        period = validated(PeriodSerializer, request.query_params)
        expenses = pro.linked_expenses(customer, period.get("from"), period.get("to"), project_id=project.id)
        data = {
            "project": pro.projects_with_counts(customer).get(pk=project.pk),
            "totals": pro.expense_totals(expenses),
            "categories": pro.expenses_by_category(expenses, category_name(request)),
        }
        return ok(ProjectSummarySerializer(data).data)

    @extend_schema(
        summary="PRO project items",
        description="Linked order items of the project with their amounts (as in the summary), newest order "
                    "first, paginated." + FORBIDDEN_NOTE,
        parameters=PERIOD_PARAMETERS + PAGE_PARAMETERS,
        responses={200: ProjectItemSerializer(many=True)},
        tags=TAGS,
    )
    def project_items(self, request, pk):
        customer = pro.pro_customer(request)
        project = self._project(request, pk, customer)
        params = validated(PeriodPageSerializer, request.query_params)
        expenses = pro.linked_expenses(customer, params.get("from"), params.get("to"), project_id=project.id)
        return ok(get_pro_paginator(expenses, params["page"], params["page_size"], ProjectItemSerializer,
                                    {"request": request}))

    @extend_schema(
        summary="PRO dashboard",
        description="Totals of every project of the customer (active and archived, zeros included) and goods by "
                    "root category (adds up to `totals.goods`)." + FORBIDDEN_NOTE,
        parameters=PERIOD_PARAMETERS,
        responses={200: DashboardSerializer},
        tags=TAGS,
    )
    def dashboard(self, request):
        customer = pro.pro_customer(request)
        period = validated(PeriodSerializer, request.query_params)
        expenses = pro.linked_expenses(customer, period.get("from"), period.get("to"))
        data = {
            "totals": pro.expense_totals(expenses),
            "projects": pro.expenses_by_project(expenses, pro.Project.objects.filter(customer=customer)),
            "categories": pro.expenses_by_category(expenses, category_name(request)),
        }
        return ok(DashboardSerializer(data).data)

    @extend_schema(
        summary="Orders with unlinked items",
        description="Customer's not canceled orders with at least one item not linked to a project, newest "
                    "first." + FORBIDDEN_NOTE,
        parameters=PAGE_PARAMETERS,
        responses={200: UnlinkedOrderSerializer(many=True)},
        tags=TAGS,
    )
    def unlinked_orders(self, request):
        customer = pro.pro_customer(request)
        params = validated(PeriodPageSerializer, request.query_params)
        return ok(get_pro_paginator(pro.orders_with_unlinked_items(customer), params["page"], params["page_size"],
                                    UnlinkedOrderSerializer, {"request": request}))

    @extend_schema(
        summary="Link order items to a project",
        description="Links every item of the order (no `item_ids`) or the given ones to the active project. "
                    "Items linked to another project → 409 (`error_code` 37, `detail.conflicting_item_ids`), "
                    "nothing changed; send again with `force: true` to move them. Canceled order → 400 (39), "
                    "archived project → 400 (38), someone else's order / project → 404." + FORBIDDEN_NOTE,
        request=LinkItemsSerializer,
        responses={200: LinkResultSerializer},
        tags=TAGS,
    )
    def order_link(self, request, pk):
        customer = pro.pro_customer(request)
        data = validated(LinkItemsSerializer, request.data)
        order = pro.link_items(customer, pk, data["project_id"], data.get("item_ids"), data["force"])
        return ok(LinkResultSerializer(order).data)

    @extend_schema(
        summary="Unlink order items",
        description="Removes the project from every item of the order (no `item_ids`) or the given ones."
                    + FORBIDDEN_NOTE,
        request=UnlinkItemsSerializer,
        responses={200: LinkResultSerializer},
        tags=TAGS,
    )
    def order_unlink(self, request, pk):
        customer = pro.pro_customer(request)
        data = validated(UnlinkItemsSerializer, request.data)
        order = pro.unlink_items(customer, pk, data.get("item_ids"))
        return ok(LinkResultSerializer(order).data)
