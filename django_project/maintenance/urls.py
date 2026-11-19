from rest_framework.routers import DefaultRouter

from .views import EquipmentViewSet, MaintenanceRequestViewSet

router = DefaultRouter()
router.register("equipment", EquipmentViewSet, basename="equipment")
router.register("requests", MaintenanceRequestViewSet, basename="request")

urlpatterns = router.urls
