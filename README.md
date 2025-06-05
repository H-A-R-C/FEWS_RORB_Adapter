# RORB-FEWS-adapter
---
## About
RORB model adapter developed for Snowy Hydrological Forecasting System (S-HEWS)

---
## Installation
**1. Clone the repository**
Start by cloning the repository to your local machine:
```bash
git clone https://github.com/H-A-R-C/FEWS_RORB_Adapter.git
```

**2. Create a python virtual environment**
Navigate to the RORB-FEWS-adapter folder and create a virtual environment:
```bash
python -m venv .venv
```

**3. Activate the virtual environment**
On Windows:
```bash
.\.venv\Scripts\activate
```

**4. Install project dependencies**

Install the necessary dependencies for module access:

```bash
pip install .
```

For development purposes, install additional development dependencies:

```bash
pip install .[dev]
```

**5. Update project dependencies**

Before packaging, ensure that all project dependencies are up-to-date. Navigate to the project directory and install the latest dependencies:

```bash
pip install -e . 
```

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





