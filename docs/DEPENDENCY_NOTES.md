# Dependency Notes & Known Conflicts

This document explains critical dependency constraints in SeeWhozThere and why certain versions are pinned.

## Critical Constraint: numpy < 2.0

**The most important rule:** `numpy` must always be **less than version 2.0**.

This constraint exists because of an irreconcilable conflict between two packages:

| Package | numpy Requirement |
|---------|------------------|
| `hailort 4.23.0` (Hailo SDK) | `numpy < 2.0` |
| `opencv-python-headless >= 4.9` | `numpy >= 2.0` |

The Hailo SDK is installed system-wide by Hailo's own installer and cannot be easily changed. Therefore, we must constrain our pip packages to respect it.

**Resolution:** Pin `opencv-python-headless==4.8.1.78` and `numpy>=1.24.3,<2.0.0`. OpenCV 4.8 works perfectly with numpy 1.x and provides all the features SeeWhozThere needs.

## Why We Use a Virtual Environment

Running `pip install` system-wide on a Raspberry Pi running Debian Bookworm or Trixie will produce the "externally managed environment" error. More importantly, system-wide installs can conflict with Hailo SDK packages.

The `setup.sh` script creates a **Python virtual environment** (`venv/`) that:

1. Isolates SeeWhozThere's dependencies from the system Python.
2. Prevents accidental upgrades from breaking the Hailo SDK.
3. Makes the installation reproducible and portable.
4. Allows the systemd services to use the exact correct Python interpreter.

## Upgrading Dependencies Safely

Before upgrading any package, check compatibility:

```bash
# Activate the virtual environment
source venv/bin/activate

# Check what version of numpy Hailo requires
python3 -c "import hailo_platform; print('Hailo OK')"

# Only then upgrade, and always test afterwards
pip install "numpy>=1.24.3,<2.0.0"
```

**Never run `pip install --upgrade` without checking the Hailo SDK constraints first.**

## Full Dependency Tree

```
SeeWhozThere
├── fastapi>=0.104.1,<0.112.0
│   ├── starlette
│   └── pydantic
├── uvicorn[standard]
├── jinja2
├── python-multipart
├── opencv-python-headless==4.8.1.78   ← PINNED (numpy < 2 compatibility)
├── numpy>=1.24.3,<2.0.0               ← PINNED (Hailo SDK requirement)
├── pillow
└── pytz

System-installed (NOT via pip):
└── hailort==4.23.0                    ← Requires numpy < 2
    ├── contextlib2
    └── future
```
