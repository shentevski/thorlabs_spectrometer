"""
thorlabs_spectrometer
=====================
Friendly Python control for Thorlabs **CCT-series** compact spectrometers
(CCT10 and siblings), wrapping the vendor ``pyCCT`` SDK.

    from thorlabs_spectrometer import Spectrometer, list_spectrometers

    print(list_spectrometers())
    with Spectrometer() as spec:
        spec.exposure_ms = 8.3
        spec.hw_average = 5
        spec.acquire_dark()
        spec.snap().to_csv("spectrum.csv")

See the package README and ``examples/`` for more.
"""

from ._dll import DLL_DIR, resolve_dll_dir
from .spectrometer import (
    Spectrometer,
    SpectrometerError,
    Spectrum,
    list_spectrometers,
)

__all__ = [
    "Spectrometer",
    "Spectrum",
    "SpectrometerError",
    "list_spectrometers",
    "resolve_dll_dir",
    "DLL_DIR",
]
__version__ = "0.1.0"
