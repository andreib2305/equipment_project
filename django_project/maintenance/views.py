from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .audit import log_request_event
from .models import Equipment, MaintenanceRequest
from .serializers import (
    EquipmentSerializer,
    MaintenanceRequestSerializer,
    RequestStatusSerializer,
)


def request_payload(obj: MaintenanceRequest) -> dict:
    """Полезная нагрузка события аудита для заявки."""

    return {
        "id": obj.pk,
        "equipment_id": obj.equipment_id,
        "equipment_inventory_number": obj.equipment.inventory_number,
        "description": obj.description,
        "priority": obj.priority,
        "status": obj.status,
        "created_at": obj.created_at.isoformat(),
    }


class EquipmentViewSet(viewsets.ModelViewSet):
    """CRUD для оборудования: /api/equipment/."""

    queryset = Equipment.objects.all()
    serializer_class = EquipmentSerializer
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ("inventory_number", "name")
    ordering_fields = ("inventory_number", "name", "status")
    ordering = ("inventory_number",)


class MaintenanceRequestViewSet(viewsets.ModelViewSet):
    """CRUD для заявок: /api/requests/.

    Дополнительные эндпоинты:
    * PATCH /api/requests/{id}/status/ — смена статуса;
    * GET /api/requests/?status=open&priority=high — фильтрация.
    """

    queryset = MaintenanceRequest.objects.select_related("equipment")
    serializer_class = MaintenanceRequestSerializer
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ("description", "equipment__inventory_number", "equipment__name")
    ordering_fields = ("created_at", "priority", "status")
    ordering = ("-created_at",)

    def get_queryset(self):
        queryset = super().get_queryset()
        status_value = self.request.query_params.get("status")
        priority = self.request.query_params.get("priority")
        equipment_id = self.request.query_params.get("equipment")

        if status_value:
            queryset = queryset.filter(status=status_value)
        if priority:
            queryset = queryset.filter(priority=priority)
        if equipment_id:
            queryset = queryset.filter(equipment_id=equipment_id)
        return queryset

    def perform_create(self, serializer):
        instance = serializer.save()
        log_request_event("request.created", instance.pk, request_payload(instance))

    def perform_update(self, serializer):
        previous_status = serializer.instance.status
        instance = serializer.save()
        event_type = (
            "request.status_changed"
            if previous_status != instance.status
            else "request.updated"
        )
        log_request_event(event_type, instance.pk, request_payload(instance))

    def perform_destroy(self, instance):
        payload = request_payload(instance)
        request_id = instance.pk
        instance.delete()
        log_request_event("request.deleted", request_id, payload)

    @action(detail=True, methods=["patch"], url_path="status")
    def set_status(self, request, pk=None):
        instance = self.get_object()
        serializer = RequestStatusSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        previous_status = instance.status
        instance = serializer.save()

        if previous_status != instance.status:
            log_request_event(
                "request.status_changed", instance.pk, request_payload(instance)
            )

        return Response(
            MaintenanceRequestSerializer(instance).data, status=status.HTTP_200_OK
        )
