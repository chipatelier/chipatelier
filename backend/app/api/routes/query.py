"""Click-to-inspect layout query endpoint.

GET /api/v1/query/{run_id}?x_um=&y_um=&tolerance_um=

Downloads the highest completed stage ODB from MinIO to a temp directory,
runs OpenROAD inside the ORFS container image as a subprocess with a Python
script that performs a linear bounding-box scan of all instances, and returns
matching element details (name, master cell type, connected net names).

Security guarantees:
- Run ownership verified before any file access (403 for non-owners)
- Container runs with --network none, --cap-drop ALL, read-only mount
- Temp directory cleaned up in finally block — no ODB files left on disk
- 30-second subprocess timeout prevents hanging on large designs
"""
import json
import os
import shutil
import subprocess
import tempfile
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models.run import Run
from app.models.user import User
from app.schemas.query import InspectElement, InspectResponse
from app.services.storage_service import StorageService

router = APIRouter()

# OpenROAD Python script — runs inside the ORFS container.
# CRITICAL: Uses linear scan of getInsts() — there is NO native spatial index
# in OpenDB. Do NOT attempt queryRegion or R-tree methods.
_QUERY_SCRIPT_TEMPLATE = """
import odb
import json

db = odb.dbDatabase.create()
odb.read_db(db, "{odb_path}")
chip = db.getChip()
block = chip.getBlock()
dbu = block.getDbUnitsPerMicron()

x_dbu = int({x_um} * dbu)
y_dbu = int({y_um} * dbu)
tol_dbu = int({tolerance_um} * dbu)

results = []
for inst in block.getInsts():
    bbox = inst.getBBox()
    if (bbox.xMin() - tol_dbu <= x_dbu <= bbox.xMax() + tol_dbu and
            bbox.yMin() - tol_dbu <= y_dbu <= bbox.yMax() + tol_dbu):
        master = inst.getMaster()
        nets = [it.getNet().getName() for it in inst.getITerms() if it.getNet()]
        results.append(dict(
            name=inst.getName(),
            master=master.getName() if master else None,
            nets=nets,
        ))

print(json.dumps(results))
"""

# Stage → ODB filename mapping (highest stage produces most informative results)
_STAGE_ODB_MAP: dict[str, str] = {
    "finish":    "6_final.odb",
    "route":     "5_route.odb",
    "cts":       "4_cts.odb",
    "place":     "3_place.odb",
    "floorplan": "2_floorplan.odb",
    "synth":     "1_synth.odb",
}


@router.get("/query/{run_id}", response_model=InspectResponse, tags=["query"])
async def click_to_inspect(
    run_id: uuid.UUID,
    x_um: float = Query(..., description="X coordinate in microns"),
    y_um: float = Query(..., description="Y coordinate in microns"),
    tolerance_um: float = Query(default=1.0, description="Search tolerance in microns"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InspectResponse:
    """Query layout at a specific point and return matching cell instances.

    Downloads the run's ODB file from MinIO, runs OpenROAD inside the ORFS
    container image to perform a linear instance scan, and returns matching
    elements within tolerance_um microns of (x_um, y_um).

    Returns an empty elements list when no instance is found at the click point.
    """
    settings = get_settings()

    # --- 1. Fetch run with project relationship for ownership check ---
    stmt = (
        select(Run)
        .options(selectinload(Run.project))
        .where(Run.id == run_id)
    )
    result = await db.execute(stmt)
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # --- 2. Ownership check (student can only query their own runs) ---
    if run.project.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your run")

    # --- 3. Validate artifacts exist ---
    if not run.artifact_path:
        raise HTTPException(
            status_code=400,
            detail="Run has no artifacts — complete the run first",
        )

    # --- 4. Determine ODB file from highest completed stage ---
    stage = run.stage_completed or "route"
    odb_filename = _STAGE_ODB_MAP.get(stage, "5_route.odb")
    odb_minio_key = f"{run.artifact_path}/{odb_filename}"

    # --- 5. Download ODB to temp directory ---
    tmpdir = tempfile.mkdtemp(prefix="chipatelier_query_")
    odb_local_path = os.path.join(tmpdir, odb_filename)

    try:
        storage = StorageService(settings)
        storage.download_file_to_path(odb_minio_key, odb_local_path)

        # --- 6. Build OpenROAD Python query script ---
        script = _QUERY_SCRIPT_TEMPLATE.format(
            odb_path=odb_local_path,
            x_um=x_um,
            y_um=y_um,
            tolerance_um=tolerance_um,
        )

        # --- 7. Run OpenROAD inside ORFS container (read-only, no network) ---
        cmd = [
            "docker", "run", "--rm",
            "--network", "none",
            "--user", "orfs:orfs",
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "-v", f"{tmpdir}:{tmpdir}:ro",
            settings.ORFS_IMAGE,
            "openroad", "-python", "-e", script,
        ]

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if proc.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"OpenROAD query failed: {proc.stderr[:500]}",
            )

        # --- 8. Parse and return results ---
        elements_raw: list[dict] = json.loads(proc.stdout.strip() or "[]")
        elements = [InspectElement(**e) for e in elements_raw]

        return InspectResponse(
            elements=elements,
            run_id=str(run_id),
            x_um=x_um,
            y_um=y_um,
        )

    finally:
        # Always clean up temp dir — no ODB files left on disk
        shutil.rmtree(tmpdir, ignore_errors=True)
