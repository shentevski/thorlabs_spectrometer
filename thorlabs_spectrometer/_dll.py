"""
_dll.py
=======
Locate the Thorlabs Compact Spectrograph **.NET (net48) assemblies** that the
vendor ``pyCCT`` package loads through pythonnet.

This is the spectrometer-side equivalent of ``thorlabs_camera/_dll.py``, except
the CCT SDK ships its DLLs *inside* the vendor package (``pyCCT/net48/``), so
that bundled folder is the primary location.

Resolution order (first match wins):

1. an explicit ``dll_dir`` argument,
2. the ``THORLABS_CCT_DLL_DIR`` environment variable,
3. the bundled ``pyCCT/net48`` folder shipped with this repo
   (present when run from a clone or an editable ``pip install -e .``),
4. a standard Thorlabs CCT SDK install location.

On non-Windows machines nothing is loaded, so the package still imports
cleanly on a Mac/Linux box where you edit the code (the DLLs only *run* on
Windows).
"""

from __future__ import annotations

import os
from pathlib import Path

# repo_root/thorlabs_spectrometer/_dll.py  ->  repo_root/pyCCT/net48
_BUNDLED_DLL_DIR = Path(__file__).resolve().parent.parent / "pyCCT" / "net48"

# Best-effort fallbacks if someone runs against an official SDK install
# instead of the bundled copy. Adjust if your installer used another path.
_STANDARD_DIRS = [
    Path(r"C:\Program Files\Thorlabs\CCT\net48"),
    Path(r"C:\Program Files\Thorlabs\Compact Spectrometers\net48"),
]

ENV_VAR = "THORLABS_CCT_DLL_DIR"


def resolve_dll_dir(dll_dir=None) -> Path:
    """Return the folder that holds the net48 assemblies.

    Does not verify the folder exists -- see :func:`check_dll_dir` for that.
    """
    if dll_dir is not None:
        return Path(dll_dir)
    env = os.environ.get(ENV_VAR)
    if env:
        return Path(env)
    if _BUNDLED_DLL_DIR.is_dir():
        return _BUNDLED_DLL_DIR
    for candidate in _STANDARD_DIRS:
        if candidate.is_dir():
            return candidate
    # Fall back to the bundled path even when missing, so the error message
    # points at the place a user is most likely able to fix.
    return _BUNDLED_DLL_DIR


def check_dll_dir(dll_dir=None) -> Path:
    """Resolve the DLL folder and raise a helpful error if it isn't there."""
    resolved = resolve_dll_dir(dll_dir)
    driver = resolved / "Thorlabs.ManagedDevice.CompactSpectrographDriver.dll"
    if not resolved.is_dir():
        raise FileNotFoundError(
            f"Thorlabs CCT DLL folder not found:\n  {resolved}\n"
            "Make sure the 'pyCCT/net48' folder was pulled with the repo, set "
            f"the {ENV_VAR} environment variable, or pass dll_dir=... explicitly."
        )
    if not driver.is_file():
        raise FileNotFoundError(
            f"Folder exists but the driver assembly is missing:\n  {driver}\n"
            "The DLL folder looks incomplete -- re-pull the repo or point "
            f"{ENV_VAR} at a full net48 folder."
        )
    return resolved


# Best-guess default at import time (handy for printing/inspection).
DLL_DIR = resolve_dll_dir()
