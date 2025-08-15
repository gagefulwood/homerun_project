from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework import status as drf_status
from api.serializers import DeviceSerializer, ServerSerializer
from api.models import Device, Server

class DeviceViewSet(viewsets.ModelViewSet):
    '''
    POST /api/devices/ - Register a device
    GET /api/devices/ - List devices
    PATCH /api/devices/{id} - Update a device's status
    '''
    queryset = Device.objects.all().order_by('id')
    serializer_class = DeviceSerializer
    permission_classes = [AllowAny]
    http_method_names = ['get', 'post', 'patch']



class ServerViewSet(viewsets.ModelViewSet):
    '''
    POST /api/servers/ - Create a new server
    GET /api/servers/ - List all servers
    GET /api/servers/{id} - Get a specific server's details
    PATCH /api/servers/{id} - Update a specific server's status
    '''
    queryset = Server.objects.select_related('device').order_by('id')
    serializer_class = ServerSerializer
    permission_classes = [AllowAny]
    http_method_names = ['get', 'post', 'patch']
                
