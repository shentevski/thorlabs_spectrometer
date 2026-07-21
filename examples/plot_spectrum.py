"""
plot_spectrum.py
================
Acquire a spectrum and plot it with matplotlib.

    pip install matplotlib
    python examples/plot_spectrum.py
"""

import matplotlib.pyplot as plt

from thorlabs_spectrometer import Spectrometer

EXPOSURE_MS = 8.3
HW_AVERAGE = 5


def main():
    with Spectrometer() as spec:
        spec.exposure_ms = EXPOSURE_MS
        spec.hw_average = HW_AVERAGE
        spec.acquire_dark()
        spectrum = spec.snap()
        device = spec.device_id

    plt.plot(spectrum.wavelengths, spectrum.intensities, lw=0.8)
    plt.xlabel("Wavelength (nm)")
    plt.ylabel("Intensity (counts)")
    plt.title(
        f"{device} - {spectrum.exposure_ms} ms x {spectrum.hw_average} frames"
    )
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig("spectrum.png", dpi=150)
    print("Saved spectrum.png")
    plt.show()


if __name__ == "__main__":
    main()
