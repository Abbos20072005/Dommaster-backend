from rest_framework import serializers

from apps.authorization.models import Customer
from apps.service.models import ORDER_CHANNEL, SearchRequest, SearchSynonym
from apps.service.search import normalize
from .dashboard import DateRangeQuerySerializer

MAX_SYNONYM_TERMS = 20


class SearchSynonymSerializer(serializers.ModelSerializer):
    terms = serializers.ListField(
        child=serializers.CharField(max_length=100), min_length=2, max_length=MAX_SYNONYM_TERMS,
        help_text='Equivalent terms, e.g. ["6203 2RS", "6203-2RS", "180203"]: a query with one of them also '
                  'looks for the others. Case, spaces and dashes do not matter.')

    class Meta:
        model = SearchSynonym
        fields = ("id", "terms", "is_active", "created_at", "updated_at")
        read_only_fields = ("created_at", "updated_at")

    def validate_terms(self, terms):
        cleaned, seen = [], set()
        for term in terms:
            key = normalize(term)
            if not key:
                raise serializers.ValidationError("A term must not be empty.")
            if key not in seen:
                seen.add(key)
                cleaned.append(term.strip())
        if len(cleaned) < 2:
            raise serializers.ValidationError("At least two different terms.")
        return cleaned


class NotFoundSearchQuerySerializer(DateRangeQuerySerializer):
    """?days= (default 30, ending today) or ?date_from=&date_to=, plus the language / platform."""
    language = serializers.ChoiceField(choices=("uz", "ru"), required=False, help_text="Language of the search")
    platform = serializers.ChoiceField(choices=ORDER_CHANNEL, required=False,
                                       help_text="site / ios / android (searches without it are in `all` only)")


class NotFoundSearchExportQuerySerializer(NotFoundSearchQuerySerializer):
    export_language = serializers.ChoiceField(choices=("ru", "uz"), default="ru", help_text="Language of the headers")


class NotFoundSearchRowSerializer(serializers.Serializer):
    query = serializers.CharField(source="normalized", help_text="The query in lower case, words joined by a space")
    searches = serializers.IntegerField(help_text="Searches with no result in the range")
    viewers = serializers.IntegerField(help_text="Distinct customers / devices that made them")
    languages = serializers.ListField(child=serializers.CharField())
    first_searched_at = serializers.DateTimeField()
    last_searched_at = serializers.DateTimeField()


class SearchRequestCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ("id", "full_name", "phone_number")


class SearchRequestAdminSerializer(serializers.ModelSerializer):
    customer = SearchRequestCustomerSerializer(read_only=True)

    class Meta:
        model = SearchRequest
        fields = ("id", "query", "phone_number", "company", "customer", "language", "platform", "status",
                  "manager_comment", "created_at", "updated_at")
        read_only_fields = ("query", "phone_number", "company", "language", "platform", "created_at", "updated_at")
