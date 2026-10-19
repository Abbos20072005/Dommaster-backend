from rest_framework import serializers
from apps.authorization.models import Customer
from apps.service import pro
from apps.service.models import Project

MONEY = {"max_digits": 18, "decimal_places": 2}


class ProjectCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ("id", "full_name", "phone_number", "account_type")


class ProjectSerializer(serializers.ModelSerializer):
    customer = ProjectCustomerSerializer(read_only=True)
    items_count = serializers.IntegerField(read_only=True, default=0, help_text="Linked order items")
    orders_count = serializers.IntegerField(read_only=True, default=0, help_text="Orders with linked items")

    class Meta:
        model = Project
        fields = ("id", "customer", "name", "address", "comment", "status", "archived_at", "items_count",
                  "orders_count", "created_at", "updated_at")
        read_only_fields = fields


class ProjectExpensesSerializer(serializers.Serializer):
    goods = serializers.DecimalField(**MONEY)
    delivery = serializers.DecimalField(**MONEY)
    total = serializers.DecimalField(**MONEY)
    orders_count = serializers.IntegerField()
    items_count = serializers.IntegerField()


class ProjectCategoryExpenseSerializer(serializers.Serializer):
    id = serializers.IntegerField(allow_null=True)
    name = serializers.CharField(allow_null=True)
    goods = serializers.DecimalField(**MONEY)


class ProjectDetailSerializer(ProjectSerializer):
    expenses = serializers.SerializerMethodField(help_text="All time, as the customer sees it (paid, not canceled)")
    categories = serializers.SerializerMethodField()

    class Meta(ProjectSerializer.Meta):
        fields = ProjectSerializer.Meta.fields + ("expenses", "categories")
        read_only_fields = fields

    def _expenses(self, obj):
        if not hasattr(obj, "_expenses"):
            obj._expenses = pro.linked_expenses(obj.customer, project_id=obj.id)
        return obj._expenses

    def get_expenses(self, obj) -> ProjectExpensesSerializer:
        return ProjectExpensesSerializer(pro.expense_totals(self._expenses(obj))).data

    def get_categories(self, obj) -> ProjectCategoryExpenseSerializer(many=True):
        rows = pro.expenses_by_category(self._expenses(obj), lambda category: category.name_ru)
        return ProjectCategoryExpenseSerializer(rows, many=True).data
