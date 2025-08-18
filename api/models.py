from django.db import models
import re

class Device(models.Model):
    name = models.CharField(max_length=255)
    is_online = models.BooleanField(default=True)
    last_seen = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Device({self.id}): {self.name}"

class ServerStatus(models.TextChoices):
    STOPPED = 'stopped', "Stopped"
    STARTING = 'starting', "Starting"
    RUNNING = 'running', "Running"
    ERROR =  'error', "Error"

    @classmethod
    def transitions(cls):
        '''
        Defines the valid state transitions for server status transitions.
        Keys are the starting statuses, and the values are allowed transitions
        '''
        return {
        cls.STOPPED: {cls.STARTING},
        cls.STARTING: {cls.RUNNING, cls.ERROR},
        cls.RUNNING: {cls.STOPPED},
        cls.ERROR: {cls.STARTING},
    }

class Server(models.Model):
    name = models.CharField(max_length=50)
    subdomain = models.CharField(max_length=50, unique=True)
    status = models.CharField(
        max_length=10,
        choices=ServerStatus.choices,
        default=ServerStatus.STOPPED,
    )
    device = models.ForeignKey(
        to=Device,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="servers",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Automatically regenerates the subdomain when the name of the server is changed
        if not self.pk or Server.objects.get(pk=self.pk).name != self.name:
            self.subdomain = self._generate_subdomain()
        super().save(*args, **kwargs)

    def _generate_subdomain(self):
        '''
        Creates a unique, URL-friendly subdomain from the server name
        1. Converts name to lowercase
        2. Replaces spaces and special characters with hyphens
        3. Appends a number if the subdomain generated already exists
        '''
        # Create the base subdomain from the name
        base = re.sub(r'[^a-zA-Z0-9]+', '-', self.name.lower()).strip('-')
        subdomain = base
        num = 1
        # Checks for uniqueness and appends a number if a collision is found
        while Server.objects.filter(subdomain__iexact=subdomain).exclude(pk=self.pk).exists():
            subdomain = f"{subdomain}-{num}"
            num += 1
        return subdomain

    def __str__(self):
        return f"Server({self.id}): {self.name} [{self.status}]"