"""Celery application instance."""
from celery import Celery

app = Celery("chipatelier")
app.config_from_object("worker.celeryconfig")
app.autodiscover_tasks(["worker.tasks"])
