from django.db import transaction
from rest_framework import serializers
from .models import Device, Server, _ALLOWED


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
    
    def validate_status(self, value):
        instance: Server
        if instance and instance.status != value:
            allowed = _ALLOWED[instance.status]
            if value not in allowed:
                raise serializers.ValidationError(
                    f"Cannot transition from {instance.status} -> {value}."
                )
        return value
    
    @transaction.atomic
    def update(self, instance, validated):
        new_status: str | None = validated.get("status")
        if new_status == Server.ServerStatus.STARTING and instance.status != new_status:
            device = (
                Device.objects.filter(is_online=True, servers__isnull=True)
                .order_by("last_seen")
                .first()
            )
            if device:
                validated["device"] = device
            else:
                validated["status"] = Server.ServerStatus.ERROR
        return super().update(instance, validated)