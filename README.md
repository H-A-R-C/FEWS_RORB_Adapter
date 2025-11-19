# RORB-FEWS-adapter
---
## About
RORB model adapter developed for Snowy Hydrological Forecasting System (S-HEWS)

---
## Installation
**1. Clone the repository**
```bash
git clone https://github.com/H-A-R-C/FEWS_RORB_Adapter.git
cd FEWS_RORB_Adapter
```

**2. Install uv (one-time)**
```bash
pip install uv
```

**3. Sync dependencies**
Create the virtual environment and install runtime + dev dependencies in one go:
```bash
uv sync
```
The default environment lives in `.venv`. Activate it on Windows with:
```bash
.\.venv\Scripts\activate
```

**4. Editable installs / extras**
If you prefer to stick with pip tooling use:
```bash
pip install -e ".[dev]"
```
Both paths pull the same dependencies defined in `pyproject.toml`.

**6. Distribute the executable**
 
Make sure datas are set in the pre_adapter_talbingo.spec file:
```python
datas=[
   ('src/rorb_config.json', 'src'),
   ('src/fews_config.json', 'src'),
   ('src/file_mapping.json', 'src')
   ]
```

Package the RORB adapter scripts into standalone executables using PyInstaller. Run the following commands:

```bash
pyinstaller pre_adapter_talbingo.spec
pyinstaller post_adapter_talbingo.spec
```

To produce reproducible builds from scratch:
```bash
uv pip install pyinstaller
uv run pyinstaller pre_adapter_talbingo.spec
uv run pyinstaller post_adapter_talbingo.spec
```

---
## Usage
* Run pre-adapter in cmd: pre_adapter_talbingo.exe %runinfo_filepath%
* Run post-adapter in cmd: post_adapter_talbingo.exe %runinfo_filepath%
---
## New Features
* Change adapter into executables, including the creation of run_rorb.bat by the pre-adapter
* Introduce fews_config, file_mapping and rorb_config JSON files for model and system settings
* Set up a unit testing framework for future development and debugging
* Add log messaging for missing data
* Add adapter architecture documentation in \docs





