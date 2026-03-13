# OpenROAD Flow Scripts (ORFS) - Complete Documentation

## Overview

OpenROAD Flow Scripts (ORFS) is a complete RTL-to-GDS physical design flow that runs inside a Docker container. This document explains how it works based on running the GCD (Greatest Common Divisor) test case.

## Directory Structure

The ORFS container has the following structure:

```
/OpenROAD-flow-scripts/flow/
├── Makefile                    # Main ORFS Makefile
├── scripts/                    # TCL and shell scripts for each flow stage
│   ├── variables.mk           # Variable definitions
│   ├── synth.tcl              # Synthesis script
│   ├── floorplan.tcl          # Floorplanning script
│   └── ...
├── designs/                    # Design files directory (DESIGN_HOME)
│   ├── src/                   # Verilog source files (shared across platforms)
│   │   └── gcd/
│   │       └── gcd.v          # GCD Verilog implementation
│   └── sky130hd/              # Platform-specific configs (PLATFORM/DESIGN_NICKNAME/)
│       └── gcd/
│           ├── config.mk      # Design configuration
│           └── constraint.sdc # Timing constraints
├── platforms/                  # PDK platform files (PLATFORM_HOME)
│   └── sky130hd/
│       ├── config.mk          # Platform configuration
│       ├── lib/               # Liberty timing files
│       ├── lef/               # LEF physical layout files
│       └── ...
└── results/                    # Output directory (created during flow)
    └── PLATFORM/DESIGN_NICKNAME/VARIANT/
        ├── 1_synth.odb        # Synthesis output database
        ├── 2_floorplan.odb    # Floorplan output
        ├── 3_place.odb        # Placement output
        └── ...
```

## Key ORFS Variables

These variables control the flow and must be set correctly:

| Variable | Default | Description |
|----------|---------|-------------|
| `DESIGN_CONFIG` | (required) | Path to config.mk file (e.g., `designs/sky130hd/gcd/config.mk`) |
| `DESIGN_HOME` | `$(FLOW_HOME)/designs` | Root directory for design files |
| `DESIGN_NAME` | (set in config.mk) | Name of the design (e.g., "gcd") |
| `DESIGN_NICKNAME` | `$(DESIGN_NAME)` | Nickname for the design (defaults to DESIGN_NAME) |
| `PLATFORM` | (set in config.mk) | PDK platform name (e.g., "sky130hd") |
| `PLATFORM_HOME` | `$(FLOW_HOME)/platforms` | Root directory for platform files |
| `FLOW_HOME` | `/OpenROAD-flow-scripts/flow` | ORFS installation directory |
| `FLOW_VARIANT` | `base` | Flow variant name (for running multiple configs) |

## config.mk File Structure

The `config.mk` file defines the design and points to required files:

```makefile
# From designs/sky130hd/gcd/config.mk

export DESIGN_NAME = gcd
export PLATFORM    = sky130hd

# Verilog source files - uses ORFS variables
export VERILOG_FILES = $(DESIGN_HOME)/src/$(DESIGN_NICKNAME)/gcd.v

# Timing constraints - platform-specific
export SDC_FILE = $(DESIGN_HOME)/$(PLATFORM)/$(DESIGN_NICKNAME)/constraint.sdc

# Design parameters
export CORE_UTILIZATION = 40
export TNS_END_PERCENT = 100
export EQUIVALENCE_CHECK = 1
```

### Variable Expansion Example:
Given:
- `DESIGN_HOME = /OpenROAD-flow-scripts/flow/designs`
- `DESIGN_NICKNAME = gcd`
- `PLATFORM = sky130hd`

The variables expand to:
- `VERILOG_FILES = /OpenROAD-flow-scripts/flow/designs/src/gcd/gcd.v`
- `SDC_FILE = /OpenROAD-flow-scripts/flow/designs/sky130hd/gcd/constraint.sdc`

## Running the ORFS Flow

### Command Structure

```bash
cd /OpenROAD-flow-scripts/flow
make DESIGN_CONFIG=<path-to-config.mk> [target]
```

### Common Targets

| Target | Description |
|--------|-------------|
| (default) | Run complete flow: synthesis → floorplan → place → CTS → route → finishing |
| `synth` | Run only synthesis |
| `floorplan` | Run up to floorplanning |
| `place` | Run up to placement |
| `route` | Run up to routing |
| `finish` | Run complete flow to GDS |

### Example: Running GCD Design

```bash
# Full flow
make DESIGN_CONFIG=designs/sky130hd/gcd/config.mk

# Just synthesis
make DESIGN_CONFIG=designs/sky130hd/gcd/config.mk synth
```

## Flow Stages and Outputs

The flow progresses through these stages:

1. **Synthesis (1_synth)**
   - Input: Verilog RTL
   - Output: `1_synth.odb`, `1_synth.v` (gate-level netlist)
   - Tool: Yosys

2. **Floorplan (2_floorplan)**
   - Input: Synthesized netlist
   - Output: `2_floorplan.odb`
   - Creates die area, places I/O pins, power grid

3. **Placement (3_place)**
   - Input: Floorplan
   - Output: `3_place.odb`
   - Places standard cells

4. **Clock Tree Synthesis (4_cts)**
   - Input: Placement
   - Output: `4_cts.odb`
   - Builds clock distribution network

5. **Routing (5_route)**
   - Input: CTS result
   - Output: `5_route.odb`
   - Routes all nets

6. **Finishing (6_final)**
   - Input: Routed design
   - Output: `6_final.gds`, `6_final.def`
   - Final checks, GDS generation

## Test Run Results

### Synthesis Stage (Successful)

```
$ make DESIGN_CONFIG=designs/sky130hd/gcd/config.mk synth

Output files created:
- results/sky130hd/gcd/base/1_synth.odb         # OpenROAD database
- results/sky130hd/gcd/base/1_synth.sdc         # Timing constraints
- results/sky130hd/gcd/base/1_2_yosys.v         # Gate-level netlist
- results/sky130hd/gcd/base/clock_period.txt    # Clock period value

Elapsed time: ~3 seconds
Peak memory: ~120 MB
```

## How to Adapt for ChipAtelier

### Required Directory Structure in Container

ChipAtelier downloads user files to `/workspace/`. To match ORFS expectations, we need:

```
/workspace/
├── config.mk                    # User's config file
└── src/
    └── design/                  # DESIGN_NICKNAME directory
        ├── *.v                  # Verilog files
        └── *.sdc                # SDC file (optional, can be in config dir)
```

### Required Makefile Command

```bash
cd /OpenROAD-flow-scripts/flow
make \
  DESIGN_CONFIG=/workspace/config.mk \
  DESIGN_HOME=/workspace \
  DESIGN_NICKNAME=design
```

### Required config.mk Format for Users

Users must provide a config.mk that uses ORFS variables:

```makefile
export DESIGN_NAME = gcd
export PLATFORM    = sky130hd

# Use ORFS variables - these will be set by ChipAtelier
export VERILOG_FILES = $(DESIGN_HOME)/src/$(DESIGN_NICKNAME)/gcd.v
export SDC_FILE      = $(DESIGN_HOME)/src/$(DESIGN_NICKNAME)/constraint.sdc

# Design parameters
export CORE_UTILIZATION = 40
export CLOCK_PERIOD = 1.1
```

## Important Notes

1. **DESIGN_HOME must match file locations**: If files are in `/workspace/src/design/`, then `DESIGN_HOME=/workspace` and `DESIGN_NICKNAME=design`

2. **SDC files**: Can be specified in config.mk or auto-generated. If specified, the path must exist.

3. **Platform files**: Already included in the ORFS Docker image at `/OpenROAD-flow-scripts/flow/platforms/`

4. **Results directory**: Created automatically at `results/PLATFORM/DESIGN_NICKNAME/VARIANT/`

5. **Error handling**: If a file path is wrong, ORFS will fail early with clear error messages

## Verification

To verify the setup works:

```bash
# Test that the container can run
docker run --rm openroad/orfs:latest bash -c "cd /OpenROAD-flow-scripts/flow && ls -la"

# Test GCD example synthesis
docker run --rm openroad/orfs:latest bash -c \
  "cd /OpenROAD-flow-scripts/flow && \
   make DESIGN_CONFIG=designs/sky130hd/gcd/config.mk synth"

# Check results
docker run --rm openroad/orfs:latest bash -c \
  "cd /OpenROAD-flow-scripts/flow && \
   ls -la results/sky130hd/gcd/base/1_synth.odb"
```

## Common Issues

1. **"PLATFORM variable not set"**: config.mk missing or `PLATFORM` not exported
2. **"File not found"**: `VERILOG_FILES` or `SDC_FILE` paths don't match actual file locations
3. **"No such file or directory"**: `DESIGN_CONFIG` path is wrong
4. **Permission errors**: Container user doesn't have write access to results directory

## References

- ORFS Documentation: https://openroad-flow-scripts.readthedocs.io/
- OpenROAD Documentation: https://openroad.readthedocs.io/
- SKY130 PDK: https://skywater-pdk.readthedocs.io/
