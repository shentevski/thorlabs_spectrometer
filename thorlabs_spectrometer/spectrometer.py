"""
spectrometer.py
===============
Friendly, blocking Python control for Thorlabs **CCT-series** compact
spectrometers (CCT10 and siblings).

This wraps the vendor ``pyCCT`` package that ships with the Compact
Spectrograph SDK, the same way ``thorlabs_camera`` wraps ``thorlabs_tsi_sdk``.
What you get on top of raw ``pyCCT``:

* a real context manager (``with Spectrometer() as spec:``) -- ``pyCCT.PyCCT``
  defines ``__exit__`` but no ``__enter__``, so ``with`` fails on it,
* properties instead of get/set pairs (``spec.exposure_ms = 8.3``),
* exceptions instead of silent ``False`` / ``(None, None, 0, 0)`` returns,
* ``acquire_dark()`` as one call (close shutter -> record dark -> reopen),
* spectra as numpy arrays in a tidy ``Spectrum`` tuple with ``.to_csv()``,
* lazy DLL loading, so this module still imports on macOS/Linux for editing.

Example
-------
    from thorlabs_spectrometer import Spectrometer

    with Spectrometer() as spec:
        spec.exposure_ms = 8.3
        spec.hw_average = 5
        spec.acquire_dark()
        spec.snap().to_csv("spectrum.csv")
"""

from __future__ import annotations

import csv
import logging
import platform
from typing import NamedTuple, Optional

import numpy as np

from ._dll import check_dll_dir

__all__ = ["Spectrometer", "Spectrum", "SpectrometerError", "list_spectrometers"]


class SpectrometerError(RuntimeError):
    """The spectrometer rejected a command, or an acquisition failed."""


class Spectrum(NamedTuple):
    """One acquired spectrum, plus the settings actually used for it."""

    wavelengths: np.ndarray  # nm
    intensities: np.ndarray  # counts (dark-subtracted if a dark was recorded)
    exposure_ms: float       # exposure the sensor really used
    hw_average: int          # frames the hardware averaged

    def to_csv(self, path) -> None:
        """Write the spectrum as a two-column CSV with a header row."""
        with open(path, "w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["Wavelength (nm)", "Intensity"])
            writer.writerows(zip(self.wavelengths, self.intensities))

    def __len__(self) -> int:
        return len(self.wavelengths)


def _load_pycct():
    """Import the vendor ``pyCCT`` package. Windows-only, done lazily.

    Kept out of module scope because ``pyCCT`` does ``import clr`` at import
    time, which would make this whole package unimportable on a Mac.
    """
    if platform.system() != "Windows":
        raise RuntimeError(
            "The Thorlabs CCT DLLs are Windows-only. You can edit this package "
            "anywhere, but it must be RUN on the Windows PC the spectrometer is "
            "plugged into."
        )
    try:
        from pyCCT import PyCCT
    except ImportError as exc:  # pragma: no cover - depends on install state
        raise ImportError(
            "Could not import the vendor 'pyCCT' package.\n"
            "Install this repo in editable mode from the clone root:\n"
            "    pip install -e .\n"
            "and make sure pythonnet is installed:\n"
            "    pip install pythonnet"
        ) from exc
    return PyCCT


def _new_session(dll_dir=None, *, virtual=False, ethernet_ip=None, verbose=False):
    """Build a configured ``PyCCT`` session (DLLs loaded, discovery not yet run)."""
    resolved = check_dll_dir(dll_dir)
    PyCCT = _load_pycct()

    if not verbose:
        # pyCCT calls logging.basicConfig(level=INFO) at import and chatters on
        # every call; quiet the Python side down unless asked. (The SDK's own
        # .NET console logger is separate and stays at Information.)
        logging.getLogger("pyCCT.pyCCT").setLevel(logging.WARNING)

    session = PyCCT(str(resolved))

    # Both of these must be configured *before* discovery runs.
    if ethernet_ip is not None:
        session.register_ethernet_ip_address(ethernet_ip)
    if virtual:
        session.set_with_virtual(True)
    return session


def list_spectrometers(dll_dir=None, *, virtual=False, ethernet_ip=None) -> list[str]:
    """Return the device IDs of all discoverable CCT spectrometers.

    Opens and closes its own short-lived session, so it is safe to call before
    constructing a :class:`Spectrometer`.
    """
    session = _new_session(dll_dir, virtual=virtual, ethernet_ip=ethernet_ip)
    try:
        return list(session.discover_devices())
    finally:
        session.stop()


class Spectrometer:
    """A connected Thorlabs CCT-series spectrometer.

    Parameters
    ----------
    device_id:
        Which device to open. Defaults to the first one discovered, which is
        what you want when only one spectrometer is plugged in.
    dll_dir:
        Override the net48 DLL folder. Defaults to the bundled ``pyCCT/net48``.
    virtual:
        Open the SDK's simulated device instead of real hardware -- handy for
        testing the code path with nothing plugged in.
    ethernet_ip:
        Register an IP address so an Ethernet-connected unit is discoverable.
    verbose:
        Leave pyCCT's INFO-level Python logging switched on.
    """

    def __init__(
        self,
        device_id: Optional[str] = None,
        *,
        dll_dir=None,
        virtual: bool = False,
        ethernet_ip: Optional[str] = None,
        verbose: bool = False,
    ):
        self._session = _new_session(
            dll_dir, virtual=virtual, ethernet_ip=ethernet_ip, verbose=verbose
        )
        self._spec = None
        try:
            found = list(self._session.discover_devices())
            if not found:
                raise SpectrometerError(
                    "No CCT spectrometer found. Check the USB/Ethernet cable and "
                    "that no other program (e.g. the Thorlabs GUI) holds the "
                    "device open. Pass virtual=True to test without hardware."
                )
            if device_id is None:
                device_id = found[0]
            elif device_id not in found:
                raise SpectrometerError(
                    f"Spectrometer {device_id!r} not found. Discovered: {found}"
                )

            self._spec = self._session.connect_to_device(device_id)
            if self._spec is None:
                raise SpectrometerError(f"Failed to connect to {device_id!r}.")
        except Exception:
            # Never leak the SDK session if construction fails partway.
            self._session.stop()
            raise

    # -- lifecycle ---------------------------------------------------------

    def __enter__(self) -> "Spectrometer":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        """Release the device. Safe to call more than once."""
        if self._session is not None:
            self._session.stop()
            self._session = None
            self._spec = None

    def _require_open(self):
        if self._spec is None:
            raise SpectrometerError("Spectrometer is closed.")
        return self._spec

    def __repr__(self) -> str:
        if self._spec is None:
            return "<Spectrometer (closed)>"
        return f"<Spectrometer {self.device_id!r} exposure={self.exposure_ms} ms>"

    # -- identity ----------------------------------------------------------

    @property
    def device_id(self) -> str:
        return self._require_open().get_device_id()

    # -- acquisition settings ---------------------------------------------

    @property
    def exposure_ms(self) -> float:
        """Sensor exposure time in milliseconds."""
        return self._require_open().get_manual_exposure()

    @exposure_ms.setter
    def exposure_ms(self, value: float) -> None:
        if not self._require_open().set_manual_exposure(float(value)):
            raise SpectrometerError(f"Could not set exposure to {value} ms.")

    @property
    def hw_average(self) -> int:
        """Number of frames the hardware averages per acquisition."""
        return self._require_open().get_hardware_average()

    @hw_average.setter
    def hw_average(self, frames: int) -> None:
        if not self._require_open().set_hardware_average(int(frames)):
            raise SpectrometerError(f"Could not set hardware averaging to {frames}.")

    @property
    def amplitude_correction(self) -> bool:
        """Whether the SDK applies its amplitude (spectral response) correction."""
        return self._require_open().get_use_amplitude_correction()

    @amplitude_correction.setter
    def amplitude_correction(self, state: bool) -> None:
        self._require_open().set_use_amplitude_correction(bool(state))

    # -- shutter and dark reference ---------------------------------------

    def set_shutter(self, open_: bool) -> None:
        """Open (``True``) or close (``False``) the mechanical shutter.

        Already waits the ~40 ms the shutter needs to travel.
        """
        if not self._require_open().set_shutter(bool(open_)):
            raise SpectrometerError(
                f"Could not {'open' if open_ else 'close'} the shutter."
            )

    def open_shutter(self) -> None:
        self.set_shutter(True)

    def close_shutter(self) -> None:
        self.set_shutter(False)

    def acquire_dark(self) -> None:
        """Record a dark reference, subtracted from every later spectrum.

        Closes the shutter, records the dark, and reopens the shutter. Call
        this again after changing exposure or averaging -- a dark is only valid
        for the settings it was taken at.
        """
        spec = self._require_open()
        self.close_shutter()
        try:
            if not spec.update_dark_spectrum(False):
                raise SpectrometerError("Failed to acquire the dark spectrum.")
        finally:
            # Always try to reopen, even if the dark acquisition blew up.
            self.open_shutter()

    def clear_dark(self) -> None:
        """Discard the stored dark reference (stop subtracting it)."""
        if not self._require_open().update_dark_spectrum(True):
            raise SpectrometerError("Failed to clear the dark spectrum.")

    # -- hardware triggering ----------------------------------------------

    @property
    def input_trigger(self) -> tuple:
        """Current input-trigger settings: ``(enabled, ave_no_wait, falling_edge)``."""
        return tuple(self._require_open().get_input_hw_trigger_state())

    def set_input_trigger(
        self,
        enabled: bool,
        *,
        ave_no_wait: bool = False,
        falling_edge: bool = False,
    ) -> None:
        """Configure the input hardware trigger.

        ``enabled=False`` is free-running. ``ave_no_wait=True`` averages all
        frames off a single trigger event instead of one trigger per frame.
        """
        ok = self._require_open().set_input_hw_trigger(
            bool(enabled), bool(ave_no_wait), bool(falling_edge)
        )
        if not ok:
            raise SpectrometerError("Could not configure the input hardware trigger.")

    @property
    def output_trigger_delay_ms(self) -> float:
        """Delay of the output hardware trigger, in ms (negative fires early)."""
        return self._require_open().get_output_hw_trigger_delay()

    @output_trigger_delay_ms.setter
    def output_trigger_delay_ms(self, delay_ms: float) -> None:
        if not self._require_open().set_output_hw_trigger_delay(float(delay_ms)):
            raise SpectrometerError(f"Could not set output trigger delay to {delay_ms} ms.")

    # -- acquisition -------------------------------------------------------

    def snap(self) -> Spectrum:
        """Acquire one spectrum and return it as a :class:`Spectrum`."""
        wl, intensity, exposure, averaged = self._require_open().acquire_single_spectrum()
        if wl is None or intensity is None:
            raise SpectrometerError(
                "Spectrum acquisition failed. Is the exposure time valid for this "
                "device, and is the shutter open?"
            )
        return Spectrum(
            wavelengths=np.asarray(wl, dtype=float),
            intensities=np.asarray(intensity, dtype=float),
            exposure_ms=exposure,
            hw_average=averaged,
        )

    def snap_many(self, count: int) -> list[Spectrum]:
        """Acquire ``count`` spectra back to back."""
        return [self.snap() for _ in range(count)]
