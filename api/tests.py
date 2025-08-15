from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from api.models import Device, Server


class BaseAPITestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()


class ServerAPITestCase(BaseAPITestCase):
    def test_create_server_success(self):
        # POST /api/servers/ with valid payload ⇒ 201 + correct default fields
        pass

    def test_create_server_name_too_short(self):
        # Name < 3 chars ⇒ 400 with validation error
        pass

    def test_create_server_name_too_long(self):
        # Name > 50 chars ⇒ 400 with validation error
        pass

    def test_subdomain_generated_from_name(self):
        # “My Cool Server” should generate slug “my-cool-server”
        pass

    def test_get_server_detail(self):
        # GET /api/servers/{id}/ returns the full server representation
        pass

    def test_list_servers(self):
        # GET /api/servers/ lists all existing servers
        pass

    def test_starting_assigns_device_and_runs(self):
        # stopped → starting with an online device ⇒ status running + device_id set
        pass

    def test_starting_without_available_device_set_error(self):
        # stopped → starting but no devices online ⇒ status error, device null
        pass

    def test_running_to_stopped_clears_device(self):
        # running → stopped must null-out device FK
        pass

    def test_error_to_starting_retry_path(self):
        # error → starting should retry assignment logic (success or error again)
        pass

    def test_invalid_status_transition_returns_400(self):
        # e.g. running → error is illegal ⇒ 400 response
        pass

    def test_multiple_servers_can_share_device(self):
        # Verify API allows several servers to reference the same device FK
        pass

    def test_device_field_read_only_on_patch(self):
        # PATCH attempting to set device_id manually should be ignored or 400
        pass

    def test_delete_server_returns_405(self):
        # DELETE /api/servers/{id}/ must return 405 Method Not Allowed
        pass

    def test_created_at_timestamp_auto_set(self):
        # created_at (if defined) should auto-populate on POST
        pass


class DeviceAPITests(BaseAPITestCase):
    def test_create_device_success(self):
        # POST /api/devices/ with valid data ⇒ 201 + correct defaults
        pass

    def test_device_name_required(self):
        # Missing/blank name ⇒ 400 validation error
        pass

    def test_list_devices(self):
        # GET /api/devices/ returns all devices
        pass

    def test_patch_device_toggle_online_status(self):
        # PATCH is_online flip true⇄false reflected in response
        pass

    def test_last_seen_updates_on_patch(self):
        # Any successful PATCH should bump last_seen timestamp
        pass

    def test_patch_updates_name(self):
        # PATCH {name: "New"} updates name without touching is_online
        pass

    def test_device_offline_does_not_affect_running_servers(self):
        # Setting device offline must not auto-change server statuses
        pass

    def test_partial_patch_only_is_online(self):
        # PATCH with only is_online field succeeds (partial update)
        pass

    def test_delete_device_returns_405(self):
        # DELETE /api/devices/{id}/ must return 405 Method Not Allowed
        pass
