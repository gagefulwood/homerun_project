from rest_framework import serializers
from .models import Device, Server

class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = (
            'id',
            'name',
            'is_online',
            'last_seen',
        )
        read_only_fields = ('id', 'last_seen')

class ServerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Server
        fields = (
            'id',
            'name',
            'subdomain',
            'device',
            'created_at',
        )
        read_only_fields = ('id', 'subdomain', 'created_at')

    def validate_name(self, name):
        if not (3 <= len(name) <= 50):
            raise serializers.ValidationError("Server name must be between 3 and 50 characters.")
        return name