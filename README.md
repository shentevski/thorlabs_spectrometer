# thorlabs_spectrometer

Simple Python control for **Thorlabs CCT-series compact spectrometers**
(CCT10 and siblings), built on the official `pyCCT` SDK. The .NET driver DLLs
are bundled in [`pyCCT/net48/`](pyCCT/net48), so the repo is
**clone-and-run** on a fresh Windows PC.

Same workflow as the sister [`thorlabs_motion`](../thorlabs_motion) and
[`thorlabs_camera`](../thorlabs_camera) repos: **edit the code on the Mac**,
push, then **pull and run it on the Windows PC the spectrometer is plugged
into.** The package imports cleanly on macOS/Linux (the DLLs just aren't
loaded there).

> 🔒 **Keep this repo private.** It bundles Thorlabs' proprietary DLLs — fine
> for internal use, but don't redistribute publicly.

> ⚠️ **Windows only at runtime.** The CCT `net48` assemblies only run on Windows.

---

## Setup on a new Windows PC

1. Install **Python 3.8+ (64-bit)** and the **.NET Framework 4.8 runtime**
   (already present on any current Windows 10/11).
2. Install the **Thorlabs CCT Series Spectrometer Software** once, so the USB
   driver for the device is registered. (The SDK DLLs themselves come from
   this repo, so you don't need to point at the install.)
3. Clone this repo.
4. Install in **editable** mode from the clone root:
   ```powershell
   pip install -e .
   ```
   > Use `pip install -e .` (editable), **not** plain `pip install .` — a plain
   > install copies the package into site-packages, away from the bundled
   > `pyCCT/net48/` DLLs. (If you must, set the `THORLABS_CCT_DLL_DIR`
   > environment variable to the DLL folder instead.)
5. Pull in the example extras (plotting) if you want them:
   ```powershell
   pip install -r requirements.txt
   ```
6. Plug in the spectrometer and run a demo:
   ```powershell
   python examples/quickstart.py
   ```

`pythonnet` installs automatically on Windows via the dependency marker in
`pyproject.toml`; it is deliberately skipped on macOS so editing stays painless.

---

## Usage

```python
from thorlabs_spectrometer import Spectrometer, list_spectrometers

print(list_spectrometers())          # ['CCT10-...']

with Spectrometer() as spec:         # first device found
    spec.exposure_ms = 8.3           # sensor exposure, ms
    spec.hw_average  = 5             # frames averaged in hardware

    spec.acquire_dark()              # close shutter, record dark, reopen

    spectrum = spec.snap()
    spectrum.to_csv("spectrum.csv")

    print(spectrum.wavelengths)      # numpy array, nm
    print(spectrum.intensities)      # numpy array, counts (dark-subtracted)
```

`Spectrometer()` opens the first discovered device; pass a device ID to pick a
specific one. Everything is blocking — the async .NET calls are awaited for you.

### Testing with no hardware

The SDK ships a simulated device:

```python
with Spectrometer(virtual=True) as spec:
    print(spec.snap())
```

### Ethernet-connected units

```python
spec = Spectrometer(ethernet_ip="192.168.0.160")
```

---

## API

### `list_spectrometers(dll_dir=None, *, virtual=False, ethernet_ip=None) -> list[str]`
Device IDs of everything discoverable. Opens and closes its own session.

### `Spectrometer(device_id=None, *, dll_dir=None, virtual=False, ethernet_ip=None, verbose=False)`

| Property | Type | Notes |
| --- | --- | --- |
| `device_id` | `str` | read-only |
| `exposure_ms` | `float` | sensor exposure time |
| `hw_average` | `int` | frames averaged in hardware |
| `amplitude_correction` | `bool` | SDK spectral-response correction |
| `input_trigger` | `tuple` | read-only `(enabled, ave_no_wait, falling_edge)` |
| `output_trigger_delay_ms` | `float` | negative fires before acquisition |

| Method | Notes |
| --- | --- |
| `snap()` | acquire one spectrum → `Spectrum` |
| `snap_many(count)` | acquire `count` spectra → `list[Spectrum]` |
| `acquire_dark()` | close shutter → record dark → reopen |
| `clear_dark()` | discard the stored dark reference |
| `open_shutter()` / `close_shutter()` / `set_shutter(bool)` | includes the ~40 ms travel wait |
| `set_input_trigger(enabled, *, ave_no_wait=False, falling_edge=False)` | arm external triggering |
| `close()` | release the device (automatic with `with`) |

### `Spectrum`
A `NamedTuple` of `wavelengths`, `intensities` (numpy arrays), `exposure_ms`,
`hw_average`. `len(spectrum)` gives the pixel count; `.to_csv(path)` writes a
two-column CSV.

Failures raise **`SpectrometerError`** rather than returning `False` or `None`
the way raw `pyCCT` does.

> **Dark references are settings-specific.** Re-run `acquire_dark()` after
> changing `exposure_ms` or `hw_average`, or the subtraction will be wrong.

---

## Two-machine workflow

**On this Mac (master) — make changes and publish:**
```bash
git add -A
git commit -m "Describe the change"
git push
```

**On the Windows PC — get them:**
```powershell
git pull
```
No reinstall needed after a pull: `pip install -e .` is an editable install, so
the new code is picked up on the next run. Re-run `pip install -e .` only if
the dependencies in `pyproject.toml` changed.

If you ever edit directly on the Windows PC, commit and push there, then
`git pull` on the Mac — but keeping one machine authoritative avoids conflicts.

---

## Repo layout

```
thorlabs_spectrometer/          this package (the friendly wrapper)
  ├── __init__.py
  ├── _dll.py                   locates the net48 DLL folder
  └── spectrometer.py           Spectrometer, Spectrum, list_spectrometers
pyCCT/                          vendor SDK, as shipped by Thorlabs
  ├── pyCCT.py                  PyCCT + SpectrometerWrapper
  ├── pyCCT.md                  vendor API docs (UTF-16)
  └── net48/                    the .NET assemblies  ← committed on purpose
examples/                       runnable demos
CCT_example_pythonnet.py        Thorlabs' original example, kept for reference
inspect_cct_api.py              reflection dumper for the full .NET API
```

`pyCCT/` is vendor code — left exactly as Thorlabs shipped it so it can be
swapped for a newer SDK drop without touching the wrapper.

---

## Troubleshooting

**`No CCT spectrometer found`** — check the cable, and close the Thorlabs GUI:
it holds the device open exclusively. Try `Spectrometer(virtual=True)` to
confirm the software path works.

**`Could not import the vendor 'pyCCT' package`** — you're not installed. Run
`pip install -e .` from the clone root.

**`Thorlabs CCT DLL folder not found`** — the `pyCCT/net48/` folder didn't come
down with the clone, or you installed non-editable. Set
`THORLABS_CCT_DLL_DIR` to the folder, or pass `dll_dir=...`.

**`RuntimeError: ... Windows-only`** — you're on the Mac. Expected: edit here,
run there.

**Noisy console logging** — the SDK's own .NET logger runs at Information
level. The Python-side chatter is silenced by default; pass `verbose=True` to
restore it.

**Want the full driver API?** `inspect_cct_api.py` dumps every class, method
and property in the .NET assembly by reflection:
```powershell
python inspect_cct_api.py > cct_api_dump.txt
```
The wrapper covers core acquisition; the dump shows everything else available.
