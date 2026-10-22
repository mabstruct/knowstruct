from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Env:
    base_url: str
    api_key: str


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def load_env(path: Path | None = None) -> Env:
    path = path if path is not None else REPO_ROOT / ".env"
    if not path.is_file():
        raise ConfigError(f"env file not found: {path}")
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        values[name.strip()] = _unquote(value.strip())
    for name in ("PLANE_BASE_URL", "PLANE_API_KEY"):
        if not values.get(name):
            raise ConfigError(f"missing {name} in {path}")
    return Env(base_url=values["PLANE_BASE_URL"].rstrip("/"), api_key=values["PLANE_API_KEY"])
