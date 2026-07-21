"""
quickstart.py
=============
Smallest useful example: find the spectrometer, configure it, take a dark
reference, acquire one spectrum, save it to CSV.

This is the equivalent of Thorlabs' CCT_example_pythonnet.py, minus the
boilerplate. Run it on the Windows PC the spectrometer is plugged into:

    python examples/quickstart.py
"""

from thorlabs_spectrometer import Spectrometer, list_spectrometers

# Pass virtual=True to both calls below to dry-run with no hardware attached.
VIRTUAL = False


def main():
    found = list_spectrometers(virtual=VIRTUAL)
    print("Discovered spectrometers:", found or "(none)")
    if not found:
        return

    with Spectrometer(virtual=VIRTUAL) as spec:
        print("Connected to:", spec.device_id)

        spec.exposure_ms = 8.3
        spec.hw_average = 5
        print(f"Exposure {spec.exposure_ms} ms, averaging {spec.hw_average} frames")

        # Record a dark reference; it is subtracted from later spectra.
        # Re-run this after changing exposure or averaging.
        print("Acquiring dark reference...")
        spec.acquire_dark()

        spectrum = spec.snap()
        print(
            f"Got {len(spectrum)} points, "
            f"{spectrum.wavelengths[0]:.1f}-{spectrum.wavelengths[-1]:.1f} nm, "
            f"peak {spectrum.intensities.max():.1f} counts"
        )

        spectrum.to_csv("spectrum.csv")
        print("Saved spectrum.csv")


if __name__ == "__main__":
    main()
