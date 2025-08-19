from django.db import transaction
from rest_framework import serializers
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
        # Handles the business logic for server status changes

        requested = validated_data.get("status", instance.status)
        # Handles the transition to 'starting' which triggers device assignment
        if requested == ServerStatus.STARTING and instance.status != ServerStatus.STARTING:
            # Finds the first available online device
            device = (
                Device.objects
                .filter(is_online=True)
                .order_by("last_seen")
                .first()
            )
            if device:
                # If a device is found, assign it and set status to 'running' (last_seen is updated automatically by save method)
                # attach device -> server goes RUNNING
                device.save()
                validated_data["device"] = device
                validated_data["status"] = ServerStatus.RUNNING
            else:
                # If no devices are online it sets the server status to 'error'
                # no device -> immediate ERROR
                validated_data["device"] = None
                validated_data["status"] = ServerStatus.ERROR
        # Handles th transition from 'running' to 'stopped'
        elif requested == ServerStatus.STOPPED and instance.status == ServerStatus.RUNNING:
            # When a running server is stopped, clear its device assignment
            validated_data["device"] = None
        else:
            # for any other PATCH, keep the existing status if client omitted it
            validated_data.setdefault("status", instance.status)
        return super().update(instance, validated_data)