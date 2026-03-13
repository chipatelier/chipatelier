"""KLayout tile generation task stub — implemented in plan 01-05."""
from worker.celery_app import app


@app.task(name="worker.tasks.tile_generator.generate_png", queue="background")
def generate_png(run_id: str) -> None:
    """Generate layout tiles using KLayout Python API.

    Full implementation in plan 01-05 (layout viewer).
    """
    pass
