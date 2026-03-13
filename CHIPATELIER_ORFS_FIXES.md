# ChipAtelier ORFS Integration - Required Fixes

## Problem Summary

The ChipAtelier worker was failing to run ORFS jobs because the workspace structure and command didn't match ORFS expectations.

## What ORFS Expects

### Directory Structure
```
/workspace/
├── config.mk                       # Design configuration
└── src/
    └── design/                     # DESIGN_NICKNAME directory
        ├── gcd.v                   # Verilog source files
        └── constraint.sdc          # Timing constraints
```

### Make Command
```bash
cd /OpenROAD-flow-scripts/flow
make \
  DESIGN_CONFIG=/workspace/config.mk \
  DESIGN_HOME=/workspace \
  DESIGN_NICKNAME=design
```

### config.mk Requirements

User's config.mk must use ORFS path variables:

```makefile
export DESIGN_NAME = gcd
export PLATFORM    = sky130hd

# CRITICAL: Use ORFS variables, not hardcoded paths
export VERILOG_FILES = $(DESIGN_HOME)/src/$(DESIGN_NICKNAME)/gcd.v
export SDC_FILE      = $(DESIGN_HOME)/src/$(DESIGN_NICKNAME)/constraint.sdc

# Design parameters
export CORE_UTILIZATION = 40
export TNS_END_PERCENT = 100
```

## ChipAtelier Changes Required

### 1. Worker: Download Function (worker/tasks/orfs_job.py)

**Current Issue**: Downloads files flat to `/workspace/`
**Required**: Create ORFS-compatible directory structure

```python
def _download_workspace(settings: object, artifact_path: str, workspace: str) -> None:
    """Download files from MinIO and create ORFS directory structure."""
    import boto3
    from botocore.config import Config

    s3 = boto3.client(
        "s3",
        endpoint_url=f"http://{settings.MINIO_ENDPOINT}",
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )

    # Create ORFS directory structure
    src_dir = os.path.join(workspace, "src", "design")
    os.makedirs(src_dir, exist_ok=True)

    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(
        Bucket=settings.S3_BUCKET_ARTIFACTS,
        Prefix=artifact_path,
    ):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            filename = key.split("/")[-1]

            # config.mk goes to workspace root
            # Verilog and SDC files go to src/design/
            if filename.endswith(".mk"):
                dest = os.path.join(workspace, filename)
            else:
                dest = os.path.join(src_dir, filename)

            s3.download_file(settings.S3_BUCKET_ARTIFACTS, key, dest)
```

### 2. Worker: Container Command (worker/container/manager.py)

**Current Issue**: Missing DESIGN_HOME and DESIGN_NICKNAME variables
**Required**: Pass all required ORFS variables

```python
return self._client.containers.run(
    image=image,
    command=[
        "make",
        "-C", "/OpenROAD-flow-scripts/flow",
        "DESIGN_CONFIG=/workspace/config.mk",
        "DESIGN_HOME=/workspace",
        "DESIGN_NICKNAME=design",
    ],
    name=f"orfs_job_{run_id}",
    detach=True,
    network_mode="none",
    # ... rest of container config
)
```

### 3. Frontend/Backend: User Education

Users need to know how to write config.mk files. Add documentation and example:

**Example config.mk template:**
```makefile
# Required: Design name and PDK platform
export DESIGN_NAME = gcd
export PLATFORM    = sky130hd

# Required: File paths (use ORFS variables, not hardcoded paths)
export VERILOG_FILES = $(DESIGN_HOME)/src/$(DESIGN_NICKNAME)/your_design.v
export SDC_FILE      = $(DESIGN_HOME)/src/$(DESIGN_NICKNAME)/constraint.sdc

# Optional: Design parameters
export CORE_UTILIZATION = 40
export CLOCK_PERIOD = 1.1
export TNS_END_PERCENT = 100

# Optional: Disable adder mapping for GCD designs
export ADDER_MAP_FILE :=
```

### 4. Frontend: File Upload Validation

Ensure users upload required files:
- At least one `.v` or `.sv` file (Verilog)
- Exactly one `config.mk` file
- Optionally one `.sdc` file (if not auto-generated)

## Testing the Fix

### Test Script

Run this to verify the setup works:

```bash
docker run --rm openroad/orfs:latest bash -c "
# Create workspace as ChipAtelier would
mkdir -p /workspace/src/design

# Download example files
cp /OpenROAD-flow-scripts/flow/designs/src/gcd/gcd.v /workspace/src/design/
cp /OpenROAD-flow-scripts/flow/designs/sky130hd/gcd/constraint.sdc /workspace/src/design/

# Create config.mk
cat > /workspace/config.mk << 'EOF'
export DESIGN_NAME = gcd
export PLATFORM    = sky130hd
export VERILOG_FILES = \$(DESIGN_HOME)/src/\$(DESIGN_NICKNAME)/gcd.v
export SDC_FILE      = \$(DESIGN_HOME)/src/\$(DESIGN_NICKNAME)/constraint.sdc
export CORE_UTILIZATION = 40
EOF

# Run ORFS
cd /OpenROAD-flow-scripts/flow
make DESIGN_CONFIG=/workspace/config.mk DESIGN_HOME=/workspace DESIGN_NICKNAME=design synth

# Check results
ls -lh results/sky130hd/design/base/1_synth.odb
"
```

**Expected output:**
- Synthesis completes successfully
- File `1_synth.odb` exists (~2MB)
- No errors in logs

## Common User Errors to Catch

1. **Hardcoded paths in config.mk**
   ```makefile
   # WRONG
   export VERILOG_FILES = /workspace/gcd.v

   # CORRECT
   export VERILOG_FILES = $(DESIGN_HOME)/src/$(DESIGN_NICKNAME)/gcd.v
   ```

2. **Missing PLATFORM**
   ```makefile
   # WRONG - missing PLATFORM
   export DESIGN_NAME = gcd

   # CORRECT
   export DESIGN_NAME = gcd
   export PLATFORM    = sky130hd
   ```

3. **Wrong file extension**
   - Upload `.mk` file, not `.txt` or other extensions
   - ORFS expects `config.mk` specifically

## Current Implementation Status

✅ Container user issue fixed (removed orfs:orfs user)
✅ artifact_path flow fixed (backend + frontend)
✅ ORFS Makefile path fixed (-C /OpenROAD-flow-scripts/flow)
✅ Directory structure fixed (src/design/ layout)
✅ ORFS variables fixed (DESIGN_HOME, DESIGN_NICKNAME)

🔄 Ready for testing with user files

## Next Steps

1. Apply the fixes above to worker code
2. Test with real user-uploaded files
3. Add user documentation for config.mk format
4. Add frontend validation for required files
5. Consider providing config.mk templates for common designs
