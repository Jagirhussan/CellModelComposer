import json
import os

CONFIG_FILE = "config.json"

from pathlib import Path

def find_config_upwards(start=None):
    if start is None:
        start = Path.cwd()

    for directory in [start] + list(start.parents):
        candidate = directory / CONFIG_FILE
        if candidate.exists():
            return candidate

    return None

def find_config():
    # ENV variable override
    env_path = os.getenv("APP_CONFIG")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    # Look in CWD
    cwd_path = Path.cwd() / CONFIG_FILE
    if cwd_path.exists():
        return cwd_path

    # Look in script directory
    script_dir = Path(__file__).resolve().parent
    script_path = script_dir / CONFIG_FILE
    if script_path.exists():
        return script_path

    # Optionally search parents
    return find_config_upwards(script_dir)


CONFIG_PATH = find_config()
print(f"Using config located at {CONFIG_PATH}")

class AppConfig:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppConfig, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                self.config = json.load(f)
        else:
            # Default Fallback
            self.config = {
                "llm_models": {
                    "annotation": "gemini-3.0-pro",
                    "planning": "gemini-3.0-flash",
                    "coding": "gemini-3.0-flash",
                    "research": "gemini-3.0-pro"
                },
                "rate_limits": {
                    "gemini-3.0-pro": { "rpm": 2, "tpm": 125000, "rpd": 50 },
                    "gemini-3.0-flash": { "rpm": 10, "tpm": 250000, "rpd": 250 },
                    "gemini-3.0-flash-lite": { "rpm": 15, "tpm": 250000, "rpd": 1000 },
                    "gemini-2.5-flash": { "rpm": 15, "tpm": 1000000, "rpd": 200 },
                    "gemini-2.5-flash-lite": { "rpm": 30, "tpm": 1000000, "rpd": 200 },
                    "default": { "rpm": 15, "tpm": 250000, "rpd": 1000 }
                },
                "paths": {
                    "data_dir": "data",
                    "registry_file": "data/library_registry.json",
                    "cache_file": "genai_cache.json",
                    "log_file": "llm_interaction.log",
                    "user_data":"user_data"
                },
                "ingestion": {
                    "context_window_equations": 30
                }
            }
            print(f"[Config] Warning: {CONFIG_PATH} not found. Using defaults.")

    def get(self, section, key, default=None):
        return self.config.get(section, {}).get(key, default)

# Singleton instance
config = AppConfig()