"""Celery application instance."""
from celery import Celery

app = Celery("chipatelier")
app.config_from_object("celeryconfig")
app.autodiscover_tasks(["tasks"])
