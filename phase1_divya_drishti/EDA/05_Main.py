"""05_Main.py

Lightweight orchestrator. Step 1 and Step 2 remain independently executable and
own their input validation, processing, output creation, and output validation.
"""
from pathlib import Path
import importlib.util
import time

PROJECT_FOLDER = Path(__file__).resolve().parent
STEP1_SCRIPT = PROJECT_FOLDER / "01_DatasetCreation_4Status.py"
STEP2_SCRIPT = PROJECT_FOLDER / "02_DatasetCreation_AllergenSummary.py"


def load_module(script_path, module_name):
    """Load a numbered Python file without duplicating any of its business logic."""
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load {script_path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    started = time.perf_counter()
    print("Starting Sanjeevini allergen pipeline...")

    step1 = load_module(STEP1_SCRIPT, "dataset_creation_4status")
    step1.run()

    step2 = load_module(STEP2_SCRIPT, "dataset_creation_allergen_summary")
    step2.run()

    elapsed = time.perf_counter() - started
    print(f"\nPipeline complete in {elapsed:.1f}s.")


if __name__ == "__main__":
    main()
