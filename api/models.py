from django.db import models

class Device(models.Model):
    name = models.CharField(max_length=255)
    is_online = models.BooleanField(default=True)
    last_seen = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Device({self.id}): {self.name}"


class Server(models.Model):
    class StatusChoices(models.TextChoices):
        STOPPED = 'stopped', "Stopped"
        STARTING = 'starting', "Starting"
        RUNNING = 'running', "Running"
        ERROR =  'error', "Error"

    name = models.CharField(max_length=50)
    subdomain = models.CharField(max_length=50, unique=True)
    status = models.CharField(
        max_length=10,
        choices=StatusChoices.choices,
        default=StatusChoices.STOPPED,
    )
    device = models.ForeignKey(
        to=Device,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="servers",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Server({self.id}): {self.name} [{self.status}]"