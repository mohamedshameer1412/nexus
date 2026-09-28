"""Platform records owned by Django: the audit log and each officer's profile/role."""
from django.db import models


class AuditLog(models.Model):
    at = models.DateTimeField(auto_now_add=True, db_index=True)
    user_id = models.IntegerField(null=True, blank=True, db_index=True)     # engine users.id; NULL = not signed in
    action = models.CharField(max_length=80)
    method = models.CharField(max_length=8, blank=True)
    path = models.CharField(max_length=300, blank=True)
    status = models.PositiveSmallIntegerField(default=0)
    ip = models.CharField(max_length=64, blank=True)
    detail = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["-at"]

    def __str__(self):
        return f"{self.at:%Y-%m-%d %H:%M} user={self.user_id} {self.action} -> {self.status}"
