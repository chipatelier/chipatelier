#!/bin/bash
# Wait for Xvfb to be ready before launching OpenROAD GUI.
sleep 2
export DISPLAY=:99

# Pre-load student's ODB into OpenROAD GUI using ORFS's own open.tcl script.
# CRITICAL: Use open.tcl (not read_lef/read_def inline Tcl).
# open.tcl sources load.tcl and calls load_design $ODB_FILE $SDC_FILE,
# which correctly loads full design context including LEF/LIB files.
# This replicates what `make gui_cts` / `make gui_route` / `make gui_final` do.
# Reference: CLAUDE.md "VNC Container Setup (Corrected)" section.
#
# Required env vars (set by worker/tasks/vnc_session.py when spawning container):
#   VNC_ODB_PATH   — absolute path to stage ODB file inside the container workspace
#   DESIGN_CONFIG  — absolute path to config.mk (for open.tcl LEF/LIB resolution)

export ODB_FILE="${VNC_ODB_PATH}"
export DESIGN_CONFIG="${DESIGN_CONFIG:-/workspace/config.mk}"
export OPENROAD_EXE=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad

exec "$OPENROAD_EXE" -gui /OpenROAD-flow-scripts/flow/scripts/open.tcl
