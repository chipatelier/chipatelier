#!/bin/bash
# Wait for Xvfb to be ready
sleep 2
export DISPLAY=:99

# Pre-load student's DEF into OpenROAD GUI.
# VNC_DEF_PATH and VNC_LEF_PATH are set by the container environment (worker task).
# Uses Tcl scripting interface — read_lef/read_def sequence then gui::show.
openroad -gui -no_splash << 'EOF'
if {[info exists env(VNC_LEF_PATH)] && [file exists $env(VNC_LEF_PATH)]} {
    read_lef $env(VNC_LEF_PATH)
}
if {[info exists env(VNC_DEF_PATH)] && [file exists $env(VNC_DEF_PATH)]} {
    read_def $env(VNC_DEF_PATH)
}
gui::show
EOF
