from rest_framework.routers import DefaultRouter
from .views import DeviceViewSet, ServerViewSet

router = DefaultRouter()
router.register(r'devices', DeviceViewSet, basename='device')
router.register(r'servers', ServerViewSet, basename='server')

urlpatterns = router.urls
