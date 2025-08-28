from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import Device, Server, ServerStatus


class DeviceSerializer(serializers.ModelSerializer):
    detail_url = serializers.HyperlinkedIdentityField(view_name='device-detail')
    class Meta:
        model = Device
        fields = (
            'detail_url', # Allows someone browsing web api to go directly to a device instance listed
            'id', 
            'name',
            'is_online', 
            'last_seen',
        )
        read_only_fields = (
            'id',
            'last_seen', # this status will be updated by the system automatically
        ) 
    

class ServerSerializer(serializers.ModelSerializer):
    detail_url = serializers.HyperlinkedIdentityField(view_name='server-detail')
    class Meta:
        model = Server
        fields = (
            'detail_url', # Allows someone browsing web api to go directly to a server instance listed
            'id',
            'name',
            'subdomain',
            'status',
            'device',
            'created_at',
        )
        read_only_fields = (
            'id',
            'subdomain', # automatically generated on server creation
            'device', # managed by the system based on server status transtitions
            'created_at', # automatically set when the server is first created
        )

    def validate_name(self, name):
        if not (3 <= len(name) <= 50):
            raise serializers.ValidationError("Server name must be between 3 and 50 characters.")
        return name
    
    def validate_status(self, new_status):
        # Validates the requested status transition against allowed transitions defined in ServerStatus model

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
        # Device is read-only at API layer
        validated_data.pop("device", None)

        requested = validated_data.get("status", instance.status)

        # Check transitions centrally
        allowed = ServerStatus.transitions().get(instance.status, set())
        if requested not in allowed and requested != instance.status:
            raise ValidationError(
                f"Invalid transition {instance.status} -> {requested}"
            )
        # Special logic for “starting” (device assignment)
        if requested == ServerStatus.STARTING:
            device = (
                Device.objects
                .filter(is_online=True)
                .select_for_update(skip_locked=True)
                .order_by("last_seen")
                .first()
            )
            if device:
                validated_data["device"] = device
                validated_data["status"] = ServerStatus.RUNNING
            else:
                validated_data["device"] = None
                validated_data["status"] = ServerStatus.ERROR

        # running -> stopped -> clear device
        elif requested == ServerStatus.STOPPED:
            validated_data["device"] = None
            validated_data["status"] = ServerStatus.STOPPED
        else:
            validated_data.setdefault("status", instance.status)

        return super().update(instance, validated_data)