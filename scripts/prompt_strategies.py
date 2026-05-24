import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

DEFAULT_CONFIG_PATH = Path("configs/prompt_strategies.json")


@dataclass(frozen=True)
class PromptStrategy:
    id: str
    name: str
    prompt_template: str
    temperature: float = 0.2


def load_strategies(config_path: Path = DEFAULT_CONFIG_PATH) -> List[PromptStrategy]:
    data = json.loads(Path(config_path).read_text(encoding="utf-8"))
    strategies: List[PromptStrategy] = []
    for s in data.get("strategies", []):
        strategies.append(
            PromptStrategy(
                id=str(s["id"]),
                name=str(s.get("name", s["id"])),
                prompt_template=str(s["prompt_template"]),
                temperature=float(s.get("temperature", 0.2)),
            )
        )
    return strategies