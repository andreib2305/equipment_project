from rest_framework import serializers

from .models import Equipment, MaintenanceRequest


class EquipmentSerializer(serializers.ModelSerializer):
    request_count = serializers.IntegerField(source="requests.count", read_only=True)

    class Meta:
        model = Equipment
        fields = ("id", "inventory_number", "name", "status", "request_count")
        read_only_fields = ("id", "request_count")

    def validate_inventory_number(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Инвентарный номер не может быть пустым.")
        return value

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Название не может быть пустым.")
        return value


class MaintenanceRequestSerializer(serializers.ModelSerializer):
    """Сериализатор заявки.

    Валидация:
    * описание не пустое;
    * priority — только low/medium/high/critical (choices модели);
    * оборудование должно существовать (PrimaryKeyRelatedField).
    """

    equipment_inventory_number = serializers.CharField(
        source="equipment.inventory_number", read_only=True
    )
    equipment_name = serializers.CharField(source="equipment.name", read_only=True)

    class Meta:
        model = MaintenanceRequest
        fields = (
            "id",
            "equipment",
            "equipment_inventory_number",
            "equipment_name",
            "description",
            "priority",
            "status",
            "created_at",
        )
        read_only_fields = ("id", "created_at")

    def validate_description(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Описание заявки не может быть пустым.")
        return value

    def validate_priority(self, value):
        if value not in MaintenanceRequest.Priority.values:
            allowed = ", ".join(MaintenanceRequest.Priority.values)
            raise serializers.ValidationError(
                f"Недопустимый приоритет: {value}. Допустимые значения: {allowed}."
            )
        return value


class RequestStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceRequest
        fields = ("status",)
