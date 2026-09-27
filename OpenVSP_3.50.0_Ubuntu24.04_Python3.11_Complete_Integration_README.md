# OpenVSP 3.50.0 + Ubuntu 24.04 + Python 3.11.9
# Complete Installation, Commands, OpenVSP Bridge and app.py Integration

This README is for the DRDL aerodynamic GUI project.

Environment:
- Ubuntu 24.04
- Python 3.11.9
- OpenVSP 3.50.0
- PySimpleGUI
- Separate OpenVSP visualization window

Architecture:

Python 3.11.9 / app.py
        |
        v
openvsp_aircraft.py
        |
        v
OpenVSP vsp executable
        |
        v
VSPScript
        |
        v
DRDL_aircraft.vsp3
        |
        v
separate OpenVSP window

OpenVSP 3.50.0 has an official Ubuntu 24.04 build. The official Python
API documentation states that the Python version must match the version
used to compile OpenVSP. This guide therefore uses the executable +
VSPScript bridge instead of assuming native `import openvsp` compatibility
with Python 3.11.

Official pages:
https://openvsp.org/download_old.php
https://openvsp.org/pyapi_docs/latest/

======================================================================
PART 1 - UBUNTU DEPENDENCIES
======================================================================

Open Terminal.

Type:

```bash
sudo apt update
```

Then:

```bash
sudo apt upgrade -y
```

Install runtime libraries:

```bash
sudo apt install -y unzip tar gzip libgl1 libglu1-mesa libx11-6 libxext6 libxrender1 libxrandr2 libxi6 libxfixes3
```

Install Python:

```bash
sudo apt install -y python3.11 python3.11-venv python3-pip
```

Verify:

```bash
python3.11 --version
```

Expected:

```text
Python 3.11.9
```

======================================================================
PART 2 - DOWNLOAD OPENVSP 3.50.0
======================================================================

Official old-version page:

https://openvsp.org/download_old.php

Select:

OpenVSP 3.50.0 Ubuntu 24.04

If already downloaded:

```bash
ls -lh ~/Downloads | grep -i openvsp
```

======================================================================
PART 3 - EXTRACT OPENVSP
======================================================================

Create directory:

```bash
mkdir -p "$HOME/OpenVSP-3.50.0"
```

For ZIP:

```bash
unzip ~/Downloads/YOUR_OPENVSP_FILE.zip -d "$HOME/OpenVSP-3.50.0"
```

For tar.gz:

```bash
tar -xf ~/Downloads/YOUR_OPENVSP_FILE.tar.gz -C "$HOME/OpenVSP-3.50.0"
```

Find executable:

```bash
find "$HOME/OpenVSP-3.50.0" -type f -name vsp -print
```

======================================================================
PART 4 - MAKE OPENVSP EXECUTABLE
======================================================================

If the executable is `$HOME/OpenVSP-3.50.0/vsp`:

```bash
chmod +x "$HOME/OpenVSP-3.50.0/vsp"
```

If `find` returned a nested path, use that actual path.

======================================================================
PART 5 - PUT VSP ON PATH
======================================================================

If the executable is exactly `$HOME/OpenVSP-3.50.0/vsp`:

```bash
sudo ln -sf "$HOME/OpenVSP-3.50.0/vsp" /usr/local/bin/vsp
```

Verify:

```bash
which vsp
```

Then:

```bash
vsp -h
```

======================================================================
PART 6 - SET VSP_EXE
======================================================================

Current terminal:

```bash
export VSP_EXE="$(command -v vsp)"
```

Permanent:

```bash
echo 'export VSP_EXE="$(command -v vsp)"' >> ~/.bashrc
```

Reload:

```bash
source ~/.bashrc
```

Verify:

```bash
echo "$VSP_EXE"
```

======================================================================
PART 7 - CREATE DRDL PROJECT DIRECTORY
======================================================================

For a new project:

```bash
mkdir -p "$HOME/DRDL_AERO_GUI"
cd "$HOME/DRDL_AERO_GUI"
mkdir -p openvsp_output
```

If you already have the project, use its existing directory.

======================================================================
PART 8 - CREATE openvsp_aircraft.py
======================================================================

Run:

```bash
nano openvsp_aircraft.py
```

Paste:

```python
import os
import subprocess

VSP_EXE = os.environ.get("VSP_EXE", "vsp")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "openvsp_output")

if not os.path.isdir(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

MODEL_FILE = os.path.join(OUTPUT_DIR, "DRDL_aircraft.vsp3")
SCRIPT_FILE = os.path.join(OUTPUT_DIR, "DRDL_aircraft.vspscript")

DEFAULT_PARAMS = {
    "nose_len": 300.0,
    "body_len": 2700.0,
    "wing_le": 1500.0,
    "root_chord": 200.0,
    "tip_chord": 150.0,
    "semi_span": 1000.0,
    "root_th": 20.0,
    "tip_th": 5.0,
    "wing_sweep": 2.86,
    "tail_le": 2870.0,
    "root_chord1": 120.0,
    "tip_chord1": 60.0,
    "semi_span1": 100.0,
    "root_th1": 15.0,
    "tip_th1": 5.0,
    "mach": 0.2,
    "alpha": 2.0,
    "alt": 0.0,
}

BOUNDS = {
    "nose_len": (120.0, 360.0),
    "body_len": (2400.0, 3000.0),
    "wing_le": (1000.0, 2000.0),
    "root_chord": (150.0, 250.0),
    "tip_chord": (110.0, 190.0),
    "semi_span": (600.0, 1500.0),
    "root_th": (15.0, 25.0),
    "tip_th": (5.0, 11.0),
    "wing_sweep": (0.0, 70.0),
    "tail_le": (2830.0, 2910.0),
    "root_chord1": (80.0, 160.0),
    "tip_chord1": (30.0, 90.0),
    "semi_span1": (60.0, 140.0),
    "root_th1": (15.0, 21.0),
    "tip_th1": (5.0, 11.0),
    "mach": (0.2, 0.8),
    "alpha": (0.0, 20.0),
    "alt": (0.0, 6000.0),
}

def validate_parameters(params):
    data = DEFAULT_PARAMS.copy()
    if params is not None:
        data.update(params)

    for name in DEFAULT_PARAMS:
        if name not in data:
            raise ValueError(
                "Missing OpenVSP parameter: {}".format(name)
            )

    for name, bounds in BOUNDS.items():
        value = float(data[name])
        low, high = bounds

        if value < low or value > high:
            raise ValueError(
                "{}={} is outside [{}, {}]".format(
                    name, value, low, high
                )
            )

        data[name] = value

    return data

def fmt(value):
    return "{:.10g}".format(float(value))

def build_vspscript(params):
    p = validate_parameters(params)
    total_length = p["nose_len"] + p["body_len"]

    script = """
ClearVSPModel();

string fuse_id = AddGeom("FUSELAGE", "");

SetParmVal(fuse_id, "Length", "Design", %s);
SetParmVal(fuse_id, "X_Rel_Location", "XForm", 0.0);
SetParmVal(fuse_id, "Y_Rel_Location", "XForm", 0.0);
SetParmVal(fuse_id, "Z_Rel_Location", "XForm", 0.0);

string wing_id = AddGeom("WING", "");

SetParmVal(wing_id, "Span", "XSec_1", %s);
SetParmVal(wing_id, "Root_Chord", "XSec_1", %s);
SetParmVal(wing_id, "Tip_Chord", "XSec_1", %s);
SetParmVal(wing_id, "Sweep", "XSec_1", %s);
SetParmVal(wing_id, "X_Rel_Location", "XForm", %s);
SetParmVal(wing_id, "ThickChord", "XSecCurve_0", %s);
SetParmVal(wing_id, "ThickChord", "XSecCurve_1", %s);

string tail_id = AddGeom("WING", "");

SetParmVal(tail_id, "Span", "XSec_1", %s);
SetParmVal(tail_id, "Root_Chord", "XSec_1", %s);
SetParmVal(tail_id, "Tip_Chord", "XSec_1", %s);
SetParmVal(tail_id, "Sweep", "XSec_1", 0.0);
SetParmVal(tail_id, "X_Rel_Location", "XForm", %s);
SetParmVal(tail_id, "ThickChord", "XSecCurve_0", %s);
SetParmVal(tail_id, "ThickChord", "XSecCurve_1", %s);

Update();

WriteVSPFile("%s");
""" % (
        fmt(total_length),
        fmt(2.0 * p["semi_span"]),
        fmt(p["root_chord"]),
        fmt(p["tip_chord"]),
        fmt(p["wing_sweep"]),
        fmt(p["wing_le"]),
        fmt(p["root_th"] / 100.0),
        fmt(p["tip_th"] / 100.0),
        fmt(2.0 * p["semi_span1"]),
        fmt(p["root_chord1"]),
        fmt(p["tip_chord1"]),
        fmt(p["tail_le"]),
        fmt(p["root_th1"] / 100.0),
        fmt(p["tip_th1"] / 100.0),
        MODEL_FILE.replace("\\", "/")
    )

    return script

def create_aircraft(params=None, open_gui=True):
    data = validate_parameters(params)

    try:
        check = subprocess.run(
            [VSP_EXE, "-h"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
    except OSError as exc:
        raise RuntimeError(
            "OpenVSP executable could not be started.\n"
            "VSP_EXE={}\n"
            "Original error: {}".format(VSP_EXE, exc)
        )

    if check.returncode != 0:
        raise RuntimeError(
            "OpenVSP was found but could not run.\n"
            "VSP_EXE={}\n{}".format(
                VSP_EXE, check.stderr.strip()
            )
        )

    script = build_vspscript(data)

    with open(SCRIPT_FILE, "w") as f:
        f.write(script)

    if os.path.exists(MODEL_FILE):
        try:
            os.remove(MODEL_FILE)
        except OSError:
            pass

    result = subprocess.run(
        [VSP_EXE, "-script", SCRIPT_FILE],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            "OpenVSP VSPScript failed.\n\n"
            "STDOUT:\n{}\n\n"
            "STDERR:\n{}".format(
                result.stdout,
                result.stderr
            )
        )

    if not os.path.exists(MODEL_FILE):
        raise RuntimeError(
            "OpenVSP script completed, but VSP3 was not created:\n{}".format(
                MODEL_FILE
            )
        )

    if os.path.getsize(MODEL_FILE) == 0:
        raise RuntimeError("OpenVSP created an empty VSP3 file.")

    if open_gui:
        subprocess.Popen(
            [VSP_EXE, MODEL_FILE],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    return MODEL_FILE

def visualize_aircraft(params=None):
    return create_aircraft(params=params, open_gui=True)

if __name__ == "__main__":
    print("Creating DRDL OpenVSP aircraft...")

    model = create_aircraft(
        params=DEFAULT_PARAMS,
        open_gui=True
    )

    print("OpenVSP model created:")
    print(model)
```

Save:

```text
CTRL+O
ENTER
CTRL+X
```

======================================================================
PART 9 - TEST THE OPENVSP BRIDGE
======================================================================

```bash
python3.11 -c "import openvsp_aircraft; print('IMPORT OK')"
```

Then:

```bash
python3.11 openvsp_aircraft.py
```

Check:

```bash
ls -lh openvsp_output
```

Expected:

```text
DRDL_aircraft.vsp3
DRDL_aircraft.vspscript
```

Direct script test:

```bash
vsp -script openvsp_output/DRDL_aircraft.vspscript
```

======================================================================
PART 10 - APP.PY INTEGRATION
======================================================================

Do not replace your existing predictor/optimizer/envelope GUI with a
guessed application. Add this integration layer to your existing app.py.

At the top:

```python
import threading
import PySimpleGUI as sg

from openvsp_aircraft import visualize_aircraft
```

Add outside the event loop:

```python
def launch_openvsp_visualization(params, window=None):
    def worker():
        try:
            model_file = visualize_aircraft(params)

            if window is not None:
                window.write_event_value(
                    "-OPENVSP-DONE-",
                    model_file
                )

        except Exception as exc:
            if window is not None:
                window.write_event_value(
                    "-OPENVSP-ERROR-",
                    str(exc)
                )

    thread = threading.Thread(
        target=worker,
        daemon=True
    )

    thread.start()
```

Add:

```python
def get_openvsp_params(values):
    return {
        "nose_len": float(values["nose_len"]),
        "body_len": float(values["body_len"]),
        "wing_le": float(values["wing_le"]),
        "root_chord": float(values["root_chord"]),
        "tip_chord": float(values["tip_chord"]),
        "semi_span": float(values["semi_span"]),
        "root_th": float(values["root_th"]),
        "tip_th": float(values["tip_th"]),
        "wing_sweep": float(values["wing_sweep"]),
        "tail_le": float(values["tail_le"]),
        "root_chord1": float(values["root_chord1"]),
        "tip_chord1": float(values["tip_chord1"]),
        "semi_span1": float(values["semi_span1"]),
        "root_th1": float(values["root_th1"]),
        "tip_th1": float(values["tip_th1"]),
        "mach": float(values["mach"]),
        "alpha": float(values["alpha"]),
        "alt": float(values["alt"]),
    }
```

IMPORTANT:
The GUI keys must match the actual keys in your existing app.py.

======================================================================
PART 11 - MAIN/INPUT TAB
======================================================================

Button:

```python
sg.Button(
    "Visualize in OpenVSP",
    key="-MAIN-VISUALIZE-"
)
```

Event:

```python
if event == "-MAIN-VISUALIZE-":
    try:
        params = get_openvsp_params(values)

        launch_openvsp_visualization(
            params,
            window
        )

        sg.popup_quick_message(
            "Generating OpenVSP aircraft...",
            auto_close_duration=2,
            non_blocking=True
        )

    except Exception as exc:
        sg.popup_error(
            "OpenVSP Visualization Error",
            str(exc)
        )
```

======================================================================
PART 12 - COMMON OPENVSP EVENTS
======================================================================

Success:

```python
if event == "-OPENVSP-DONE-":
    model_file = values["-OPENVSP-DONE-"]

    sg.popup_quick_message(
        "OpenVSP aircraft created successfully.",
        auto_close_duration=2,
        non_blocking=True
    )

    print("OpenVSP model:")
    print(model_file)
```

Error:

```python
if event == "-OPENVSP-ERROR-":
    error_message = values["-OPENVSP-ERROR-"]

    sg.popup_error(
        "OpenVSP Error",
        error_message
    )
```

======================================================================
PART 13 - OPTIMIZER TAB
======================================================================

After Differential Evolution creates the best geometry:

```python
best_geometry = {
    "nose_len": best_values[0],
    "body_len": best_values[1],
    "wing_le": best_values[2],
    "root_chord": best_values[3],
    "tip_chord": best_values[4],
    "semi_span": best_values[5],
    "root_th": best_values[6],
    "tip_th": best_values[7],
    "wing_sweep": best_values[8],
    "tail_le": best_values[9],
    "root_chord1": best_values[10],
    "tip_chord1": best_values[11],
    "semi_span1": best_values[12],
    "root_th1": best_values[13],
    "tip_th1": best_values[14],
    "mach": best_values[15],
    "alpha": best_values[16],
    "alt": best_values[17],
}
```

Then:

```python
launch_openvsp_visualization(
    best_geometry,
    window
)
```

Button:

```python
sg.Button(
    "Visualize Best Geometry",
    key="-OPT-VISUALIZE-"
)
```

Event:

```python
if event == "-OPT-VISUALIZE-":
    try:
        launch_openvsp_visualization(
            best_geometry,
            window
        )
    except Exception as exc:
        sg.popup_error(
            "OpenVSP Optimizer Visualization Error",
            str(exc)
        )
```

======================================================================
PART 14 - FLIGHT ENVELOPE TAB
======================================================================

Use the same backend:

```python
current_geometry = {
    "nose_len": float(values["nose_len"]),
    "body_len": float(values["body_len"]),
    "wing_le": float(values["wing_le"]),
    "root_chord": float(values["root_chord"]),
    "tip_chord": float(values["tip_chord"]),
    "semi_span": float(values["semi_span"]),
    "root_th": float(values["root_th"]),
    "tip_th": float(values["tip_th"]),
    "wing_sweep": float(values["wing_sweep"]),
    "tail_le": float(values["tail_le"]),
    "root_chord1": float(values["root_chord1"]),
    "tip_chord1": float(values["tip_chord1"]),
    "semi_span1": float(values["semi_span1"]),
    "root_th1": float(values["root_th1"]),
    "tip_th1": float(values["tip_th1"]),
    "mach": float(values["selected_mach"]),
    "alpha": float(values["selected_alpha"]),
    "alt": float(values["selected_alt"]),
}
```

Then:

```python
launch_openvsp_visualization(
    current_geometry,
    window
)
```

Button:

```python
sg.Button(
    "Visualize Current Geometry",
    key="-ENV-VISUALIZE-"
)
```

======================================================================
PART 15 - TEST COMPLETE GUI
======================================================================

```bash
cd "$HOME/DRDL_AERO_GUI"
```

```bash
export VSP_EXE="$(command -v vsp)"
```

```bash
python3.11 app.py
```

Test:

1. Main/Input.
2. Default geometry.
3. Visualize in OpenVSP.
4. Confirm fuselage.
5. Confirm main wing.
6. Confirm tail wing.
7. Change geometry.
8. Visualize again.
9. Test Optimizer visualization.
10. Test Flight Envelope visualization.

======================================================================
PART 16 - OPTIONAL START SCRIPT
======================================================================

```bash
nano run_drdl_gui.sh
```

Paste:

```bash
#!/bin/bash

export VSP_EXE="$(command -v vsp)"

cd "$(dirname "$0")"

python3.11 app.py
```

Save:

```text
CTRL+O
ENTER
CTRL+X
```

Then:

```bash
chmod +x run_drdl_gui.sh
```

Run:

```bash
./run_drdl_gui.sh
```

======================================================================
PART 17 - TROUBLESHOOTING
======================================================================

If `vsp` is not found:

```bash
which vsp
```

Then:

```bash
find "$HOME" -type f -name vsp 2>/dev/null
```

If `vsp -h` fails, fix the OpenVSP installation before debugging app.py.

If the Python bridge cannot be imported:

```bash
python3.11 -c "import openvsp_aircraft; print('IMPORT OK')"
```

If the VSP3 file is not created:

```bash
vsp -script openvsp_output/DRDL_aircraft.vspscript
```

Then:

```bash
ls -lh openvsp_output/DRDL_aircraft.vsp3
```

If the GUI freezes, make sure the OpenVSP call is inside the background
thread shown above.

If native `import openvsp` fails, do not copy random shared libraries.
Use the executable + VSPScript bridge.

======================================================================
PART 18 - 18 PARAMETERS
======================================================================

Geometry:
1. nose_len
2. body_len
3. wing_le
4. root_chord
5. tip_chord
6. semi_span
7. root_th
8. tip_th
9. wing_sweep
10. tail_le
11. root_chord1
12. tip_chord1
13. semi_span1
14. root_th1
15. tip_th1

Flight condition:
16. mach
17. alpha
18. alt

======================================================================
PART 19 - FINAL VERIFICATION
======================================================================

```bash
python3.11 --version
```

```bash
which vsp
```

```bash
vsp -h
```

```bash
echo "$VSP_EXE"
```

```bash
python3.11 -c "import openvsp_aircraft; print('OpenVSP bridge import OK')"
```

```bash
python3.11 openvsp_aircraft.py
```

```bash
ls -lh openvsp_output
```

```bash
python3.11 app.py
```

======================================================================
PART 20 - PROJECT STRUCTURE
======================================================================

DRDL_AERO_GUI/
|
+-- app.py
+-- predictor.py
+-- optimizer.py
+-- envelope.py
+-- aero_body.py
+-- openvsp_aircraft.py
+-- DRDL_aero_data_final.csv
|
+-- openvsp_output/
|   +-- DRDL_aircraft.vsp3
|   +-- DRDL_aircraft.vspscript
|
+-- de_output/
|
+-- run_drdl_gui.sh

The common backend is:

app.py
  -> launch_openvsp_visualization()
  -> openvsp_aircraft.py
  -> vsp
  -> VSPScript
  -> DRDL_aircraft.vsp3
  -> separate OpenVSP window

======================================================================
END
======================================================================
