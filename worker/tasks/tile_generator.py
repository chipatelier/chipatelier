"""KLayout PNG generation Celery task.

PERMANENT FAST-PATH: This module provides the fast-path single PNG overview of
the layout. It MUST remain as a permanent path even after Phase 2 adds the tiled
MapLibre GL viewer — the PNG is a lightweight, instant preview generated within
seconds of job completion. Never remove this functionality (CLAUDE.md constraint).

Phase 2 will add tile generation alongside this PNG (not instead of it).
"""
import logging
import os
import tempfile
from pathlib import Path

try:
    from worker.celery_app import app
except ImportError:
    from celery_app import app  # fallback when CWD is worker/ (production entrypoint)

logger = logging.getLogger(__name__)


@app.task(name="tasks.tile_generator.generate_png", queue="background", bind=True)
def generate_png(self, run_id: str, workspace: str) -> None:
    """Generate static layout PNG using KLayout Python API (headless, no X11 required).

    This is the PERMANENT fast-path preview. It must remain even after Phase 2
    adds the tiled MapLibre GL viewer. The PNG provides instant layout visibility
    within seconds of job completion.

    Source: KLayout Python API — https://www.klayout.de/doc-qt5/programming/python.html

    Pipeline:
        1. Find GDS/DEF in workspace/results/{platform}/{design}/
        2. Load via KLayout Python API (headless batch mode — no display needed)
        3. Render 2048×2048 PNG
        4. Upload to MinIO at runs/{run_id}/layout.png
        5. Also upload GDS and DEF for download links
        6. Parse PPA metrics from metadata.json
        7. Update run record in DB: artifact_path + ppa
    """
    from config import get_settings
    settings = get_settings()

    # Find results directory in workspace
    results_path = Path(workspace) / "results"
    results_dirs = list(results_path.glob("*/*")) if results_path.exists() else []
    if not results_dirs:
        logger.warning("generate_png: no results dir found in workspace %s — skipping", workspace)
        return

    results_dir = results_dirs[0]
    gds_file = results_dir / "6_final.gds"
    def_file = results_dir / "6_final.def"

    if not gds_file.exists() and not def_file.exists():
        logger.warning("generate_png: no GDS or DEF found in %s — skipping", results_dir)
        return

    tmp_path = None
    try:
        # Import KLayout — if not available in worker image, log warning and update artifact_path
        try:
            import klayout.db as db
            import klayout.lay as lay
        except ImportError:
            logger.warning(
                "generate_png: KLayout not found — layout PNG skipped. "
                "Install klayout Python package in the worker image. "
                "Artifact path will be set so download links for GDS/DEF still work."
            )
            # Still upload GDS/DEF without PNG so download links work
            _upload_artifacts(run_id, settings, gds_file, def_file, png_path=None)
            _parse_and_update(run_id, workspace, settings, results_dir)
            return

        # Create temp file for PNG output
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name

        # Load layout from GDS (preferred) or DEF
        source_path = str(gds_file) if gds_file.exists() else str(def_file)
        layout = db.Layout()
        layout.read(source_path)
        top = layout.top_cell()
        if top is None:
            logger.warning("generate_png: no top cell in layout — skipping PNG generation")
            return
        bbox = top.bbox()

        # Render headless PNG (KLayout batch mode — no DISPLAY env var needed)
        view = lay.LayoutView()
        view.load_layout(layout, True)
        view.max_hier()
        view.save_image_with_options(tmp_path, 2048, 2048, 0, 0, 0, bbox)

        logger.info("generate_png: PNG rendered to %s for run %s", tmp_path, run_id)

        # Upload PNG + artifacts to MinIO
        _upload_artifacts(run_id, settings, gds_file, def_file, png_path=tmp_path)

    except Exception as exc:
        logger.exception("generate_png: unexpected error for run %s: %s", run_id, exc)
        # Attempt to set artifact_path anyway so GDS/DEF downloads work if files exist
        try:
            _upload_artifacts(run_id, settings, gds_file, def_file, png_path=None)
        except Exception:
            pass

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    # Update DB record regardless of PNG success
    _parse_and_update(run_id, workspace, settings, results_dir)


def _upload_artifacts(
    run_id: str,
    settings,
    gds_file: Path,
    def_file: Path,
    png_path: str | None,
) -> None:
    """Upload GDS, DEF, and optionally PNG to MinIO."""
    import boto3
    from botocore.config import Config

    s3 = boto3.client(
        "s3",
        endpoint_url=f"http://{settings.MINIO_ENDPOINT}",
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        # REQUIRED for MinIO — s3v4 signature avoids 403 on presigned URLs
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )

    # Upload PNG if available (fast-path preview — permanent, never remove)
    if png_path and os.path.exists(png_path):
        png_key = f"runs/{run_id}/layout.png"
        with open(png_path, "rb") as f:
            s3.put_object(
                Bucket=settings.S3_BUCKET_ARTIFACTS,
                Key=png_key,
                Body=f,
                ContentType="image/png",
            )
        logger.info("generate_png: uploaded PNG to %s", png_key)

    # Upload GDS and DEF for download links
    for artifact_file, key_suffix in [
        (gds_file, "6_final.gds"),
        (def_file, "6_final.def"),
    ]:
        if artifact_file.exists():
            with open(artifact_file, "rb") as f:
                s3.put_object(
                    Bucket=settings.S3_BUCKET_ARTIFACTS,
                    Key=f"runs/{run_id}/{key_suffix}",
                    Body=f,
                )


def _parse_and_update(
    run_id: str,
    workspace: str,
    settings,
    results_dir: Path,
) -> None:
    """Parse PPA metrics and update the run record in DB."""
    from app.services.metrics_service import parse_ppa_metrics

    # Derive platform/design from results directory structure
    # Structure: results/{platform}/{design}/
    try:
        design = results_dir.name
        platform = results_dir.parent.name
    except Exception:
        platform = "sky130hd"
        design = "unknown"

    ppa = parse_ppa_metrics(workspace, platform, design)
    _update_run_record(run_id, settings, artifact_path=f"runs/{run_id}/", ppa=ppa)


def _update_run_record(run_id: str, settings, artifact_path: str, ppa: dict) -> None:
    """Synchronously update run record in DB from background task context."""
    import json
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session

    # Convert asyncpg URL to sync psycopg2 URL for synchronous access
    sync_url = settings.DATABASE_URL.replace(
        "postgresql+asyncpg://", "postgresql://"
    )
    try:
        engine = create_engine(sync_url)
        with Session(engine) as db_session:
            db_session.execute(
                text(
                    "UPDATE runs SET artifact_path = :ap, ppa = CAST(:ppa AS jsonb) WHERE id = CAST(:id AS uuid)"
                ),
                {"ap": artifact_path, "ppa": json.dumps(ppa), "id": run_id},
            )
            db_session.commit()
        engine.dispose()
        logger.info("generate_png: updated run %s artifact_path=%s", run_id, artifact_path)
    except Exception as exc:
        logger.exception("generate_png: failed to update run record for %s: %s", run_id, exc)
