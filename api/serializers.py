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
        read_only_fields = (
            'id',
            'subdomain',
            'device',
            'created_at',
        )

    def validate_name(self, name):
        if not (3 <= len(name) <= 50):
            raise serializers.ValidationError("Server name must be between 3 and 50 characters.")
        return name
    
    def validate_status(self, new_status):
        instance: Server = self.instance
        if not instance or new_status == instance.status:
            return new_status
        # Get the set of allowed next statuses from the current status
        allowed_transitions = ServerStatus.transitions().get(instance.status, set())
        # Check if the requested new status is in the allowed set
        if new_status not in allowed_transitions:
            raise serializers.ValidationError(
                f"Invalid status transition from '{instance.status}' to '{new_status}'."
            )
        
        return new_status
    
    @transaction.atomic
    def update(self, instance, validated_data):
        requested = validated_data.get("status", instance.status)
        if requested == ServerStatus.STARTING and instance.status != ServerStatus.STARTING:
            device = (
                Device.objects
                .filter(is_online=True)
                .order_by("last_seen")
                .first()
            )
            if device:
                # attach device → server goes RUNNING
                device.save()
                validated_data["device"] = device
                validated_data["status"] = ServerStatus.RUNNING
            else:
                # no device → immediate ERROR
                validated_data["device"] = None
                validated_data["status"] = ServerStatus.ERROR
        elif requested == ServerStatus.STOPPED and instance.status == ServerStatus.RUNNING:
            validated_data["device"] = None
        else:
            # for any other PATCH, keep the existing status if client omitted it
            validated_data.setdefault("status", instance.status)
        return super().update(instance, validated_data)