import hydra
from omegaconf import DictConfig, OmegaConf
from owl_to_python import generate_python_classes
from diff_owl import compare_owl
from converter import OntologyConverter
import os
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.resolve()


@hydra.main(version_base="1.3",
            config_path=str(PROJECT_DIR / "config"),
            config_name="config")
def evolve_model(cfg: DictConfig) -> None:
    cfg_dict = OmegaConf.to_container(cfg, resolve=True)

    # Если указан исходный файл (не OWL), конвертируем его
    if 'source_file' in cfg_dict and cfg_dict['source_file']:
        source_path = PROJECT_DIR / cfg_dict['source_file']
        owl_path = PROJECT_DIR / f"{source_path.stem}.owl"

        converter = OntologyConverter()
        converter.convert(str(source_path), str(owl_path))
        print(f"✓ Конвертировано в OWL: {owl_path}")
    else:
        owl_path = PROJECT_DIR / cfg_dict["owl_file"]

    if not owl_path.exists():
        raise FileNotFoundError(f"OWL файл не найден: {owl_path}")

    generate_python_classes(str(owl_path))
    print("✓ Python-код успешно сгенерирован")


if __name__ == "__main__":
    evolve_model()
