from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def project_root() -> Path:
    """
    Resolve the project root directory.

    In editable installs, this is the repository root containing `pyproject.toml`.
    """
    here = Path(__file__).resolve()
    for p in [here.parent, *here.parents]:
        if (p / "pyproject.toml").exists():
            return p
    return here.parent.parent


CONFIG_FILE = project_root() / "config.json"

# Default workspace directory (used when base_dir is not yet configured)
DEFAULT_WORKSPACE_DIR = Path.home() / ".microclaw"

_DEFAULT_CONFIG: dict[str, Any] = {}


def _atomic_write_text(path: Path, content: str, *, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.unlink(tmp)
        except Exception:
            pass


def _coerce_bool(val: Any, default: bool = False) -> bool:
    if isinstance(val, bool):
        return val
    if val is None:
        return default
    return str(val).strip().lower() in ("true", "1", "yes", "y", "on")


def _coerce_str(val: Any, default: str = "") -> str:
    if val is None:
        return default
    s = str(val).strip()
    return s if s else default


def _save_config_unchecked(config: dict[str, Any]) -> None:
    _atomic_write_text(
        CONFIG_FILE,
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_config() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        return dict(_DEFAULT_CONFIG)
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return {**_DEFAULT_CONFIG, **data}
    except Exception:
        return dict(_DEFAULT_CONFIG)


def save_config(config: dict[str, Any]) -> None:
    _save_config_unchecked(config)


def get_rag_mode() -> bool:
    return _coerce_bool(load_config().get("rag_mode", False), default=False)


def set_rag_mode(enabled: bool) -> None:
    config = load_config()
    config["rag_mode"] = enabled
    save_config(config)


def get_llm_config() -> dict[str, Any]:
    return load_config().get("llm", {})


def set_llm_config(llm_config: dict[str, Any]) -> None:
    cfg = load_config()
    cfg["llm"] = llm_config
    save_config(cfg)


def get_embeddings_config() -> dict[str, Any]:
    return load_config().get("embeddings", {})


def set_embeddings_config(embeddings_config: dict[str, Any]) -> None:
    cfg = load_config()
    cfg["embeddings"] = embeddings_config
    save_config(cfg)


def get_base_dir() -> str:
    """
    Return the current workspace base_dir.

    If base_dir is not configured, fall back to DEFAULT_WORKSPACE_DIR (~/.microclaw),
    persist it into config.json, and return the resolved path.
    """
    cfg = load_config()
    base_dir = cfg.get("base_dir")
    if base_dir is None or (isinstance(base_dir, str) and not str(base_dir).strip()):
        target = DEFAULT_WORKSPACE_DIR.resolve()
        cfg["base_dir"] = str(target)
        save_config(cfg)
        return str(target)
    return str(Path(str(base_dir)).resolve())


def set_base_dir(base_dir: str) -> None:
    cfg = load_config()
    cfg["base_dir"] = base_dir
    save_config(cfg)


def get_platform() -> str:
    return _coerce_str(load_config().get("platform"), default="")


def set_platform(platform: str) -> None:
    cfg = load_config()
    cfg["platform"] = platform
    save_config(cfg)


def get_tools_config() -> dict[str, Any]:
    return load_config().get("tools", {})


def set_managedb_config(tools_config: dict[str, Any]) -> dict[str, Any]:
    cfg = load_config()
    cfg["tools"] = tools_config
    save_config(cfg)
    return cfg


def get_deepagent() -> bool:
    return _coerce_bool(load_config().get("deepagent", False), default=False)


def set_deepagent(deepagent_config: bool) -> dict[str, Any]:
    cfg = load_config()
    cfg["deepagent"] = deepagent_config
    save_config(cfg)
    return cfg

