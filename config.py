import json 
from pathlib import Path 
from typing import Any 

CONFIG_FILE = Path(__file__).resolve().parent / "config.json" # use relative path to avoid hardcode

_DEFAULT_CONFIG = {}
def load_config() -> dict[str, Any]: 
    """ Load configuration from disk, returning defaults if missing"""
    if not CONFIG_FILE.exists():
        return dict(_DEFAULT_CONFIG) 
    try: 
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return {**_DEFAULT_CONFIG, **data}
    except Exception:
        return dict(_DEFAULT_CONFIG)

def save_config(config: dict[str, Any]) -> None: 
    """Persist configuration to disk"""
    CONFIG_FILE.write_text(
        json.dumps(config, ensure_ascii=False, indent=2), 
        encoding="utf-8"
    )
# ========RAG MODE========
def get_rag_mode() -> bool: 
    """Get RAG mode from configuration"""
    val = load_config().get("rag_mode", False)
    return val if isinstance(val, bool) else str(val).lower() in ("true", "1", "yes") 

def set_rag_mode(enabled: bool) -> None: 
    """
    Set RAG mode in configuration
    Example: set_rag_mode(True)
    """
    config = load_config()
    config["rag_mode"] = enabled
    save_config(config)

# ======== LLM MODE ======== 
def get_llm_config() -> dict[str, Any]:
    """Get llm configuration from configuration"""
    return load_config().get("llm", {})

def set_llm_config(llm_config: dict[str, Any]) -> None:
    """Set the llm configuration."""
    cfg = load_config()
    cfg["llm"] = llm_config
    save_config(cfg)

# ======== EMBEDDINGS ======== 
def get_embeddings_config() -> dict[str, Any]:
    """Get embeddings configuration from configuration"""
    return load_config().get("embeddings", {})

def set_embeddings_config(embeddings_config: dict[str, Any]) -> None:
    """Set the embeddings configuration."""
    cfg = load_config()
    cfg["embeddings"] = embeddings_config
    save_config(cfg)

# ======== BASE_DIR ========
def get_base_dir() -> str:
    """Get base directory (project root) from configuration."""
    base_dir = load_config().get("base_dir")
    return Path(base_dir).resolve()

def set_base_dir(base_dir: str) -> None:
    """Set the base directory in configuration."""
    cfg = load_config()
    cfg["base_dir"] = base_dir
    save_config(cfg)

# ======== PLATFORM ======== 
def get_platform() -> str:
    """Get platform from configuration"""
    return load_config().get("platform")

def set_platform(platform: str) -> None:
    """Set the platform in configuration"""
    cfg = load_config()
    cfg["platform"] = platform
    save_config(cfg)

# ======== TOOLS ========
def get_tools_config() -> dict[str, Any]:
    return load_config().get("tools", {})

def set_managedb_config(tools_config: dict[str, Any]) -> dict[str, Any]: 
    cfg = load_config()
    cfg["tools"] = tools_config
    save_config(cfg)

# ======== MCPS ========
def get_mcps_config() -> dict[str, Any]:
    return load_config().get("mcps", {})

def set_mcps_config(mcps_config: dict[str, Any]) -> dict[str, Any]: 
    cfg = load_config()
    cfg["mcps"] = mcps_config
    save_config(cfg)
  
