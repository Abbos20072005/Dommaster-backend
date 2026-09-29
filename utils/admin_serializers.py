from rest_framework import serializers
from rest_framework.utils import html


class RelationSerializer(serializers.ModelSerializer):
    """Nested relation for admin serializers: renders the related object,
    on write accepts `{"id": <pk>}` (or a bare pk) and resolves it to the model instance."""
    id = serializers.IntegerField()

    def get_fields(self):
        fields = super().get_fields()
        for name, field in fields.items():
            if name != "id":
                field.read_only = True
        return fields

    def get_value(self, dictionary):
        # multipart/form-data: accept a bare pk (`parent=5`) besides `parent.id=5`
        if html.is_html_input(dictionary) and self.field_name in dictionary:
            return dictionary.get(self.field_name)
        return super().get_value(dictionary)

    def to_internal_value(self, data):
        pk = data.get("id") if isinstance(data, dict) else data
        try:
            return self.get_queryset().get(pk=int(pk))
        except (TypeError, ValueError):
            raise serializers.ValidationError({"id": "A valid integer is required."})
        except self.Meta.model.DoesNotExist:
            raise serializers.ValidationError({"id": f"Object with id={pk} does not exist."})

    def get_queryset(self):
        return self.Meta.model.objects.all()
