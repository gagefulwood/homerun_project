from django.test import TestCase
from django.urls import reverse
from datetime import timedelta
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.test import APIClient
from api.models import Device, Server, ServerStatus

class BaseAPITestCase(TestCase):
    '''
    Base test case setting up the API client for all test classes
    '''
    def setUp(self):
        super().setUp()
        self.client = APIClient()


class DeviceRequestsTests(BaseAPITestCase):
    '''
    Tests for basic GET, POST, and Patch requests for Devices
    '''
    def test_post_device_register_device(self):
        ### Ensures a device can be created with a valid POST request ###
        response = self.client.post(
            reverse("device-list"),
            {"name": "Edge-1"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        body = response.json()
        self.assertTrue(body["is_online"])
        self.assertIsNotNone(body["last_seen"])

    def test_get_device_list_devices(self):
        ### Ensures a GET request to the devices endpoint returns all devices ###
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
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)

    def test_patch_device_update_device_status(self):
        ### Ensures a PATCH request can update a device's status ###
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
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.json()["is_online"])


class DeviceValidationTests(BaseAPITestCase):
    '''
    Tests for device data validation and constraints
    '''
    def test_device_name_is_required(self):
        ### Ensures a device cannot be created without a name ###
        response = self.client.post(
            reverse("device-list"),
            {},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_device_delete_is_not_allowed(self):
        ### Ensures DELETE requests to device endpoints return 405 ###
        device = self.client.post(
            reverse("device-list"),
            {"name": "NoDel"}, 
            format="json"
        ).json()
        response = self.client.delete(reverse("device-detail", args=[device["id"]]))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class DeviceBehaviorTests(BaseAPITestCase):
    '''
    Tests for automatic behaviors of the Device model
    '''
    def test_device_last_seen_updates_on_any_patch(self):
        ### Ensures the last_seen timestamp is updated on any PATCH request ###
        device = self.client.post(
            reverse("device-list"),
            {"name": "Clock"},
            format="json"
        ).json()
        before = Device.objects.get(pk=device["id"]).last_seen
        self.client.patch(
            reverse("device-detail", args=[device["id"]]),
            {"name": "Clock-2"},
            format="json",
        )
        after = Device.objects.get(pk=device["id"]).last_seen
        self.assertGreater(after, before)

    def test_device_offline_does_not_affect_running_servers(self):
        ### Ensure taking a device offline does not change the status of its assigned servers ###
        # Create a server and assign it to the device
        server = self.client.post(reverse("server-list"), {"name": "StayUp"}, format="json").json()
        online_device = Device.objects.create(name="Online-Node", is_online=True)
        # Start the server to assign it
        self.client.patch(
            reverse("server-detail", args=[server["id"]]),
            {"status": ServerStatus.STARTING},
            format="json",
        )
        # Now, take the device offline
        self.client.patch(
            reverse("device-detail", args=[online_device.id]),
            {"is_online": False},
            format="json",
        )
        # Verify the server is still running
        server_state = self.client.get(reverse("server-detail", args=[server["id"]])).json()
        self.assertEqual(server_state["status"], ServerStatus.RUNNING)


class ServerRequestTests(BaseAPITestCase):
    '''
    Tests for basic GET, POST, and PATCH requests for Servers
    '''
    def test_post_server_create_server(self):
        ### Ensures a server can be created with a valid POST request ###
        response = self.client.post(
            reverse("server-list"),
            {"name": "My Cool Server"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        body = response.json()
        self.assertEqual(body["status"], ServerStatus.STOPPED)
        self.assertIsNone(body["device"])

    def test_get_server_list_servers(self):
        ### Ensures a GET request to the server list endpoint returns all servers ###
        self.client.post(
            reverse("server-list"),
            {"name": "One"},
            format="json"
        )
        self.client.post(
            reverse("server-list"),
            {"name": "Two"},
            format="json"
        )
        response = self.client.get(reverse("server-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)

    def test_get_server_retrieve_specific_device(self):
        ### Ensures a GET request to a server detail endpoint returns the correct server  ###
        server = self.client.post(
            reverse("server-list"),
            {"name": "Delta"},
            format="json"
        ).json()
        url = reverse("server-detail", args=[server["id"]])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["name"], "Delta")


class ServerValidationTests(BaseAPITestCase):
    '''
    Tests for server data validation and constraints
    '''
    def test_server_creation_name_too_short(self):
        ### Ensures a server cannot be created with a name less than 3 characters long ###
        response = self.client.post(
            reverse("server-list"),
            {"name": "a"*2},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_server_creation_name_too_long(self):
        ### Ensures a server cannot be created with a name more than 50 characters long ###
        response = self.client.post(
            reverse("server-list"),
            {"name": "a"*51},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_server_deletion_is_not_allowed(self):
        ### Ensures DELETE requests to server endpoints return 405
        server = self.client.post(
            reverse("server-list"),
            {"name": "CantDel"},
            format="json"
        ).json()
        response = self.client.delete(reverse("server-detail", args=[server["id"]]))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_device_field_is_read_only(self):
        ### Ensure the device field cannot be set manually via a PATCH request ###
        device = Device.objects.create(name="Manual-Assign-Node", is_online=True)
        server = self.client.post(reverse("server-list"), {"name": "Manual"}, format="json").json()
        response = self.client.patch(
            reverse("server-detail", args=[server["id"]]),
            {"device": device.id},
            format="json",
        )
        # The serializer should ignore the 'device' field in the request data
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.json()["device"])

class ServerTransitionTests(BaseAPITestCase):
    '''
    Tests for the server status state machine and device assignment logic
    '''
    def setUp(self):
        ### Sets up a reusable online device for transition tests ###
        super().setUp()
        self.online_device = Device.objects.create(name="Online-Node", is_online=True)

    def test_server_stopped_to_starting_to_running_status_transition(self):
        ### Test transition of server status: stopped -> starting -> running ###
        server = self.client.post(reverse("server-list"), {"name": "GameServer"}, format="json").json()
        response = self.client.patch(
            reverse("server-detail", args=[server["id"]]),
            {"status": ServerStatus.STARTING},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertEqual(body["status"], ServerStatus.RUNNING)
        self.assertEqual(body["device"], self.online_device.id)

    def test_server_starts_with_no_online_device_failure(self):
        ### Test transition: stopped -> starting -> error ###
        self.online_device.is_online = False
        self.online_device.save()
        server = self.client.post(reverse("server-list"), {"name": "NoDevice"}, format="json").json()
        response = self.client.patch(
            reverse("server-detail", args=[server["id"]]),
            {"status": ServerStatus.STARTING},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertEqual(body["status"], ServerStatus.ERROR)
        self.assertIsNone(body["device"])


    def test_server_stop_running_success(self):
        ### Test transition: running -> stopped ###
        server = Server.objects.create(
            name="Runner", status=ServerStatus.RUNNING, device=self.online_device
        )
        response = self.client.patch(
            reverse("server-detail", args=[server.id]),
            {"status": ServerStatus.STOPPED},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertEqual(body["status"], ServerStatus.STOPPED)
        self.assertIsNone(body["device"])


    def test_server_retry_starting_from_error(self):
        ### Test transition: error -> starting -> running ###
        server = Server.objects.create(name="RetryServer", status=ServerStatus.ERROR)
        response = self.client.patch(
            reverse("server-detail", args=[server.id]),
            {"status": ServerStatus.STARTING},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertEqual(body["status"], ServerStatus.RUNNING)
        self.assertEqual(body["device"], self.online_device.id)

    def test_server_invalid_transitions_are_rejected(self):
        ### Ensures an invalid status transition cannot occur ###
        server = Server.objects.create(name="BadJump", status=ServerStatus.RUNNING)
        response = self.client.patch(
            reverse("server-detail", args=[server.id]),
            {"status": ServerStatus.ERROR},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_multiple_servers_can_share_one_device(self):
        ### Ensure multiple servers can be assigned to the same device ###
        server_a = self.client.post(
            reverse("server-list"),
            {"name": "Server-A"},
            format="json"
        ).json()
        server_b = self.client.post(
            reverse("server-list"),
            {"name": "Server-B"},
            format="json"
        ).json()
        # Start the first server, which assigns it to the online device
        self.client.patch(
            reverse("server-detail", args=[server_a["id"]]),
            {"status": ServerStatus.STARTING},
            format="json",
        )
        # Start the second server
        response_b = self.client.patch(
            reverse("server-detail", args=[server_b["id"]]),
            {"status": ServerStatus.STARTING},
            format="json",
        )
        # Ensure the second server was also assigned to the same device
        self.assertEqual(response_b.status_code, status.HTTP_200_OK)
        self.assertEqual(response_b.json()["device"], self.online_device.id)

class ServerBehaviorTests(BaseAPITestCase):
    '''
    Tests for automatic behaviors of the Server model
    '''
    def test_server_subdomain_is_generated_correctly(self):
        ### Ensure subdomain is a hyphenated, lowercase version of server name ###
        response = self.client.post(
            reverse("server-list"),
            {"name": "My Cool Server"},
            format="json",
        ).json()
        self.assertEqual(response["subdomain"], "my-cool-server")

    def test_server_subdomain_uniqueness_is_enforced(self):
        ### Ensure duplicate server names still result in unique, numbered subdomains ###
        first = self.client.post(
            reverse("server-list"),
            {"name": "New Server"},
            format="json"
        ).json()
        second = self.client.post(
            reverse("server-list"),
            {"name": "New Server"},
            format="json"
        ).json()
        self.assertEqual(first["subdomain"], "new-server")
        self.assertEqual(second["subdomain"], "new-server-1")

    def test_created_at_timestamp_is_auto_set(self):
        ### Ensure the created_at timestamp is set automatically on creation ###
        response = self.client.post(
            reverse("server-list"),
            {"name": "Stamp"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_at = parse_datetime(response.json()["created_at"])
        self.assertAlmostEqual(timezone.now(), created_at, delta=timedelta(seconds=5))
