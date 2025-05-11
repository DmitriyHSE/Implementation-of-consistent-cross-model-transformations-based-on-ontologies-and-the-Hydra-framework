import sys
import os
from pathlib import Path
import hydra
from omegaconf import OmegaConf, DictConfig
import importlib.util

BASE_DIR = Path(__file__).parent
GENERATED_DIR = BASE_DIR / "generated"


def load_module(module_name, path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_version(version_dir):
    print(f"\n=== Testing {version_dir} ===")
    dir_path = GENERATED_DIR / version_dir

    try:
        module = load_module(f"ontology_{version_dir}", dir_path / "ontology_model.py")

        if "v1" in version_dir:
            university = module.University(
                name="Test University",
                established=1900
            )
        else:
            university = module.University(
                name="Test University",
                founding_year=1900,
                departments=[module.Department()]
            )

        print("\nCreated University:")
        print(university)

        if hasattr(module, 'Department') and university.departments:
            print("\nDepartments:")
            for dep in university.departments:
                print(dep)

        return True
    except Exception as e:
        print(f"\nError: {str(e)}")
        return False


def test_migration(v1_dir, v2_dir):
    print("\n=== Testing Migration ===")

    try:
        module_v1 = load_module("v1", GENERATED_DIR / v1_dir / "ontology_model.py")
        module_v2 = load_module("v2", GENERATED_DIR / v2_dir / "ontology_model.py")

        sys.path.append(str(GENERATED_DIR / v2_dir))
        from compatibility import OntologyAdapter

        old_data = {
            "University": {
                "name": "Old University",
                "established": 1900
            }
        }

        migrated = OntologyAdapter.migrate(old_data, "1.0.0")
        print("\nMigrated data:")
        print(migrated)

        uni = module_v2.University(
            name=migrated["University"]["name"],
            founding_year=migrated["University"]["founding_year"],
            departments=[module_v2.Department()]  # Без передачи name
        )
        print("\nMigrated University:")
        print(uni)

        return True
    except Exception as e:
        print(f"\nMigration error: {str(e)}")
        return False
    finally:
        if str(GENERATED_DIR / v2_dir) in sys.path:
            sys.path.remove(str(GENERATED_DIR / v2_dir))


if __name__ == "__main__":
    print("=== Ontology Hydra Test ===")

    if not GENERATED_DIR.exists():
        print("\nERROR: 'generated' directory not found!")
        sys.exit(1)

    versions = sorted([
        d for d in os.listdir(GENERATED_DIR)
        if d.startswith("university_v") and (GENERATED_DIR / d).is_dir()
    ])

    if not versions:
        print("\nNo versions found")
        sys.exit(1)

    print("\nFound versions:")
    for v in versions:
        print(f"- {v}")

    results = []
    for version_dir in versions:
        results.append(test_version(version_dir))

    if len(versions) >= 2:
        results.append(test_migration(versions[0], versions[1]))

    print("\n=== Test results ===")
    print(f"Versions tested: {len(versions)}")
    print(f"Migration tested: {'Yes' if len(versions) >= 2 else 'No'}")
    print(f"Success rate: {sum(results) / len(results) * 100:.1f}%")
    print("\n=== Test completed ===")