from django.db import transaction
from rest_framework import serializers
from .models import Device, Server, ServerStatus


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
            'status',
            'device',
            'created_at',
        )
        read_only_fields = ('id', 'subdomain', 'created_at')

    def validate_name(self, name):
        if not (3 <= len(name) <= 50):
            raise serializers.ValidationError("Server name must be between 3 and 50 characters.")
        return name
    
    def validate_status(self, new_status):
        instance: Server = self.instance
        if not instance or new_status == instance.status:
            return new_status
        
        # needs to add error catching for invalid transitions
    
    @transaction.atomic
    def update(self, instance, validated_data):
        new_status = validated_data.get("status")
        if new_status == ServerStatus.STARTING and instance.status != new_status:
            device = Device.objects.filter(is_online=True, servers__isnull=True).order_by("last_seen").first()
            validated_data["device"] = device or instance.device
            if not device:
                validated_data["status"] = ServerStatus.ERROR
        return super().update(instance, validated_data)