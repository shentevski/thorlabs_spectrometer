"""
triggered_acquisition.py
========================
Use the hardware triggers: arm the input trigger so each acquisition waits for
an external edge, and offset the output trigger that fires on acquisition start.

Useful for syncing the spectrometer to a chopper, a pulsed source, or the
waveplate stages in the sister thorlabs_motion repo.

    python examples/triggered_acquisition.py
"""

from thorlabs_spectrometer import Spectrometer

N_SPECTRA = 5


def main():
    with Spectrometer() as spec:
        spec.exposure_ms = 8.3
        spec.hw_average = 1
        spec.acquire_dark()

        # Fire the output trigger 2 ms *before* the acquisition starts.
        spec.output_trigger_delay_ms = -2.0

        # Wait for a rising edge on the input trigger before each frame.
        spec.set_input_trigger(True, ave_no_wait=False, falling_edge=False)
        enabled, ave_no_wait, falling = spec.input_trigger
        print(f"Input trigger: enabled={enabled}, ave_no_wait={ave_no_wait}, falling={falling}")

        print(f"Waiting for {N_SPECTRA} external triggers...")
        for i, spectrum in enumerate(spec.snap_many(N_SPECTRA), start=1):
            print(f"  {i}: peak {spectrum.intensities.max():.1f} counts")
            spectrum.to_csv(f"triggered_{i:02d}.csv")

        # Back to free-running so the next user isn't confused by a dead device.
        spec.set_input_trigger(False)
        print("Input trigger disabled (free-running).")


if __name__ == "__main__":
    main()
