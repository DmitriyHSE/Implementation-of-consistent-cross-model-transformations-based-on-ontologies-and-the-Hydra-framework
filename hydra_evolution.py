import hydra
from omegaconf import DictConfig, OmegaConf
from owl_to_python import generate_python_classes
from diff_owl import compare_owl
import os
from pathlib import Path

# Получаем абсолютный путь к директории проекта
PROJECT_DIR = Path(__file__).parent.resolve()


@hydra.main(version_base="1.3",
            config_path=str(PROJECT_DIR / "config"),
            config_name="config")
def evolve_model(cfg: DictConfig) -> None:
    # Преобразуем конфиг в словарь и обрабатываем пути
    cfg_dict = OmegaConf.to_container(cfg, resolve=True)
    owl_path = PROJECT_DIR / cfg_dict["owl_file"]

    print(f"\nОбработка версии: {cfg_dict.get('version', 'unknown')}")
    print(f"OWL файл: {owl_path}")

    if not owl_path.exists():
        raise FileNotFoundError(f"OWL файл не найден: {owl_path}")

    # Генерация Python-кода
    generate_python_classes(str(owl_path))
    print("✓ Python-код успешно сгенерирован")


if __name__ == "__main__":
    evolve_model()