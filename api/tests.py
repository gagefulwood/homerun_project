from django.test import TestCase
from django.urls import reverse
from datetime import timedelta
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.test import APIClient
from api.models import Device, Server, ServerStatus

class BaseAPITestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()


class ServerAPITestCase(BaseAPITestCase):

    def test_create_server_success(self):
        # POST /api/servers/ with valid payload -> 201 + correct default fields
        response = self.client.post(
            reverse("server-list"),
            {"name": "My Cool Server"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        body = response.json()
        self.assertEqual(body["status"], ServerStatus.STOPPED)
        self.assertEqual(body["subdomain"], "my-cool-server")

    def test_create_server_name_too_short(self):
        # Name < 3 chars -> 400 with validation error
        response = self.client.post(
            reverse("server-list"),
            {"name": "a"*2 },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.json())

    def test_create_server_name_too_long(self):
        # Name > 50 chars -> 400 with validation error
        response = self.client.post(
            reverse("server-list"),
            {"name": "a" * 51 },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_subdomain_generated_from_name(self):
        # Subdomains should be hypenated versions of server names with duplicate prevention
        first_response = self.client.post(
            reverse("server-list"),
            {"name": "New Server"},
            format="json",
        ).json()
        second_response = self.client.post(
            reverse("server-list"),
            {"name": "New Server"},
            format="json",
        ).json()
        self.assertEqual(first_response["subdomain"], "new-server")
        self.assertEqual(second_response["subdomain"], "new-server-1")


    def test_get_server_detail(self):
        # GET /api/servers/{id}/ returns the full server representation
        server = self.client.post(
            reverse("server-list"),
            {"name": "Delta"},
            format="json",
        ).json()
        url = reverse("server-detail", args=[server["id"]])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["name"], "Delta")

    def test_list_servers(self):
        # GET /api/servers/ lists all existing servers
        self.client.post(
            reverse("server-list"),
            {"name": "One"},
            format="json",
        )
        self.client.post(
            reverse("server-list"),
            {"name": "Two"},
            format="json",
        )
        response = self.client.get(reverse("server-list"))
        self.assertEqual(len(response.json()), 2)

    def test_starting_assigns_device_and_runs(self):
        # stopped -> starting with an online device -> status running + device_id set
        device = Device.objects.create(name="Node-1", is_online=True)
        # Capture the timestamp before the action that should update it
        before_assignment_time = device.last_seen

        server_data = self.client.post(
            reverse("server-list"),
            {"name": "GameServer"},
            format="json",
        ).json()
        patch_url = reverse("server-detail", args=[server_data["id"]])
        response = self.client.patch(
            patch_url,
            {"status": ServerStatus.STARTING},
            format="json",
        )
        response_body = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response_body["status"], ServerStatus.RUNNING)
        self.assertEqual(response_body["device"], device.id)
        # Refresh the device state from the database to get the updated timestamp
        device.refresh_from_db()
        # Verify the timestamp was updated by the assignment
        self.assertGreater(device.last_seen, before_assignment_time)

    def test_starting_without_available_device_set_error(self):
        # stopped -> starting but no devices online -> status error, device null
        server = self.client.post(
            reverse("server-list"), {"name": "NoDevice"}, format="json"
        ).json()

        response = self.client.patch(
            reverse("server-detail", args=[server["id"]]),
            {"status": ServerStatus.STARTING},
            format="json",
        )
        body = response.json()
        self.assertEqual(body["status"], ServerStatus.ERROR)
        self.assertIsNone(body["device"])

    def test_running_to_stopped_clears_device(self):
        # running -> stopped must null-out device FK
        device = Device.objects.create(name="GPU-Box", is_online=True)
        server_obj = Server.objects.create(
            name="Runner",
            subdomain="runner",
            status=ServerStatus.RUNNING,
            device=device,
        )
        response = self.client.patch(
            reverse("server-detail", args=[server_obj.id]),
            {"status": ServerStatus.STOPPED},
            format="json",
        )
        body = response.json()
        self.assertEqual(body["status"], ServerStatus.STOPPED)
        self.assertIsNone(body["device"])

    def test_error_to_starting_retry_path(self):
        # error -> starting should retry assignment logic (success or error again)
        server = self.client.post(
            reverse("server-list"), {"name": "RetryServer"}, format="json"
        ).json()
        self.client.patch(
            reverse("server-detail", args=[server["id"]]),
            {"status": ServerStatus.STARTING},
            format="json",
        )

        # bring a device online and retry
        device = Device.objects.create(name="New-Node", is_online=True)
        response = self.client.patch(
            reverse("server-detail", args=[server["id"]]),
            {"status": ServerStatus.STARTING},
            format="json",
        )
        body = response.json()
        self.assertEqual(body["status"], ServerStatus.RUNNING)
        self.assertEqual(body["device"], device.id)

    def test_invalid_status_transition_returns_400(self):
        # e.g. running -> error is illegal -> 400 response
        server_obj = Server.objects.create(
            name="BadJump", subdomain="badjump", status=ServerStatus.RUNNING
        )
        response = self.client.patch(
            reverse("server-detail", args=[server_obj.id]),
            {"status": ServerStatus.ERROR},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_multiple_servers_can_share_device(self):
        # Verify API allows several servers to reference the same device FK
        device = Device.objects.create(name="Shared", is_online=True)
        server_a = self.client.post(
            reverse("server-list"), {"name": "Server-A"}, format="json"
        ).json()
        server_b = self.client.post(
            reverse("server-list"), {"name": "Server-B"}, format="json"
        ).json()

        self.client.patch(
            reverse("server-detail", args=[server_a["id"]]),
            {"status": ServerStatus.STARTING},
            format="json",
        )
        response_b = self.client.patch(
            reverse("server-detail", args=[server_b["id"]]),
            {"status": ServerStatus.STARTING},
            format="json",
        )
        self.assertEqual(response_b.json()["device"], device.id)

    def test_device_field_read_only_on_patch(self):
        # PATCH attempting to set device_id manually should be ignored or 400
        device = Device.objects.create(name="Sneaky", is_online=True)
        server = self.client.post(
            reverse("server-list"),
            {"name": "Manual"},
            format="json",
        ).json()

        response = self.client.patch(
            reverse("server-detail", args=[server["id"]]),
            {"device": device.id},
            format="json",
        )
        # 200 with unchanged FK OR 400 rejected – both valid
        self.assertIn(response.status_code, (status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST))
        if response.status_code == status.HTTP_200_OK:
            self.assertIsNone(response.json()["device"])

    def test_delete_server_returns_405(self):
        # DELETE /api/servers/{id}/ must return 405 Method Not Allowed
        server = self.client.post(
            reverse("server-list"),
            {"name": "CantDel"},
            format="json",
        ).json()
        response = self.client.delete(reverse("server-detail", args=[server["id"]]))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_created_at_timestamp_auto_set(self):
        # created_at (if defined) should auto-populate on POST
        response = self.client.post(
            reverse("server-list"),
            {"name": "Stamp"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_at = parse_datetime(response.json()["created_at"])
        self.assertIsNotNone(created_at, "created_at could not be parsed")
        now = timezone.now()
        self.assertLessEqual(now - timedelta(seconds=5), created_at)
        self.assertLessEqual(created_at, now)


class DeviceAPITests(BaseAPITestCase):

    def test_create_device_success(self):
        # POST /api/devices/ with valid data -> 201 + correct defaults
        response = self.client.post(
            reverse("device-list"),
            {"name": "Edge-1", "is_online": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        body = response.json()
        self.assertTrue(body["is_online"])
        self.assertIsNotNone(body["last_seen"])

    def test_device_name_required(self):
        # Missing/blank name -> 400 validation error
        response = self.client.post(
            reverse("device-list"),
            {},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_devices(self):
        # GET /api/devices/ returns all devices
        self.client.post(
            reverse("device-list"),
            {"name": "A"},
            format="json"
        )
        self.client.post(
            reverse("device-list"),
            {"name": "B"},
            format="json"
        )
        response = self.client.get(reverse("device-list"))
        self.assertEqual(len(response.json()), 2)

    def test_patch_device_toggle_online_status(self):
        # PATCH is_online flip boolean and be reflected in response
        device = self.client.post(
            reverse("device-list"),
            {"name": "Toggle"},
            format="json"
        ).json()
        response = self.client.patch(
            reverse("device-detail", args=[device["id"]]),
            {"is_online": False},
            format="json",
        )
        self.assertFalse(response.json()["is_online"])

    def test_last_seen_updates_on_patch(self):
        # Any successful PATCH should bump last_seen timestamp
        device = self.client.post(
            reverse("device-list"),
            {"name": "Clock"},
            format="json",
        ).json()
        before = Device.objects.get(pk=device["id"]).last_seen
        self.client.patch(
            reverse("device-detail", args=[device["id"]]),
            {"name": "Clock-2"},
            format="json",
        )
        after = Device.objects.get(pk=device["id"]).last_seen
        self.assertGreater(after, before)

    def test_patch_updates_name(self):
        # PATCH {name: "New"} updates name without touching is_online
        device = self.client.post(
            reverse("device-list"),
            {"name": "Old"},
            format="json",
        ).json()
        response = self.client.patch(
            reverse("device-detail", args=[device["id"]]),
            {"name": "New"},
            format="json",
        )
        self.assertEqual(response.json()["name"], "New")

    def test_device_offline_does_not_affect_running_servers(self):
        # Setting device offline must not auto-change server statuses
        device = self.client.post(
            reverse("device-list"),
            {"name": "Main", "is_online": True},
            format="json",
        ).json()
        server = self.client.post(
            reverse("server-list"),
            {"name": "StayUp"},
            format="json",
        ).json()
        # start server (assigns device)
        self.client.patch(
            reverse("server-detail", args=[server["id"]]),
            {"status": ServerStatus.STARTING},
            format="json",
        )
        # take device offline
        self.client.patch(
            reverse("device-detail", args=[device["id"]]),
            {"is_online": False},
            format="json",
        )
        server_state = self.client.get(reverse("server-detail", args=[server["id"]])).json()
        self.assertEqual(server_state["status"], ServerStatus.RUNNING)

    def test_partial_patch_only_is_online(self):
        # PATCH with only is_online field succeeds (partial update)
        device = self.client.post(
            reverse("device-list"),
            {"name": "Partial"},
            format="json",
        ).json()
        response = self.client.patch(
            reverse("device-detail", args=[device["id"]]),
            {"is_online": False},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.json()["is_online"])

    def test_delete_device_returns_405(self):
        # DELETE /api/devices/{id}/ must return 405 Method Not Allowed
        device = self.client.post(
            reverse("device-list"),
            {"name": "NoDel"},
            format="json",
        ).json()
        response = self.client.delete(reverse("device-detail", args=[device["id"]]))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
