from django.db import models
import re

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

    def save(self, *args, **kwargs):
        if not self.pk or Server.objects.get(pk=self.pk).name != self.name:
            self.subdomain = self._generate_subdomain()
        super().save(*args, **kwargs)

    def _generate_subdomain(self):
        base = re.sub(r'[^a-zA-Z0-9]+', '-', self.name.lower()).strip('-')
        subdomain = base
        num = 1
        while Server.objects.filter(subdomain__iexact=subdomain).exclude(pk=self.pk):
            subdomain = f"{subdomain}-{num}"
            num += 1
        return subdomain


    def __str__(self):
        return f"Server({self.id}): {self.name} [{self.status}]"