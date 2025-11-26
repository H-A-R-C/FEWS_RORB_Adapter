# FEWS–RORB Adapter Architecture

## Overview
The adapter bridges Delft-FEWS run configuration to the RORB rainfall-runoff model and back again. It consists of two Python entrypoints (pre-adapter and post-adapter) plus helper modules for parsing FEWS inputs, formatting RORB files, and converting RORB outputs into FEWS-readable XML.

## End-to-end flow
1. FEWS exports `RunInfo.xml`, parameter/state NetCDFs, and destination folders for the run.
2. `src/pre_adapter.py` reads RunInfo + NetCDF inputs, fills RORB template files under the model folder, and writes a `RUN_RORB.bat` that launches the RORB executable with the generated `.par`.
3. RORB runs via the batch file and writes `.out` plus CSV GateOps traces into the model folder.
4. `src/post_adapter.py` parses RORB outputs and produces FEWS time-series XML in the `ToFews` folder (gauge flows, reservoir operations, rainfall excess).
5. FEWS ingests the generated XML for downstream forecasting.

## Key modules
- `src/pre_adapter.py`: Orchestrates template generation. Uses `RunInfo`, `Params`, and formatter classes to write `.par`, `.stm`, snowmelt `.dat`, GateOps/transfer/override files, and `RUN_RORB.bat`.
- `src/post_adapter.py`: Processes RORB outputs. Converts GateOps CSVs to reservoir-operation XML, parses rainfall excess and selected hydrograph tables from the `.out` file, and writes FEWS time series via `XMLWriter`.
- `src/input_compiler.py`: Dataclass loaders for FEWS inputs (`RunInfo`, parameters, states, rain/meteo/transfer/operation NetCDFs). Pulls model metadata from `rorb_config.json`.
- `src/rorb_formatter.py`: Builds formatted strings for RORB inputs (PAR/STM/snow/transfer). Applies FEWS/RORB config (timestep, ordering) from `fews_config.json` and `rorb_config.json`.
- `src/utils.py`: File I/O helpers (`JsonReader`, `XMLReader`, `NetCDFReader`), template substitution (`TemplateWriter`), formatting helpers, and logging-friendly utilities reused across the adapters.
- `src/out_processing.py`: Shared output helpers for combining XML fragments and reading CSV/OUT artifacts.

## Configuration & templates
- `src/rorb_config.json`: Lists RORB elements (subareas, baseflows, dams, transfer nodes) and ordering rules used by formatters.
- `src/fews_config.json`: FEWS-side settings such as time zones and timesteps.
- `src/file_mapping.json`: Maps GateOps/transfer/output file names between templates and generated artifacts.
- Template files live under each model directory (e.g., `Model/templates/Template_*.par|stm|dat`). `TemplateWriter` substitutes placeholders with runtime values to produce model-ready files.

## Executables & packaging
- `pre_adapter_talbingo.spec` and `post_adapter_talbingo.spec` describe PyInstaller bundles for shipping the adapters as standalone executables. They include the JSON config files so packaged runs retain configuration.

## Testing workflow
- `tests/test_full_model_run.py` drives an end-to-end run using `tests/template_runinfo.xml` and fixtures in `temp_model_run/`, exercising template generation and output parsing.
- Unit-style helpers in tests clean temp folders, populate RunInfo, and can run RORB via the generated batch file when the binary is available at `bin_rorb`.
