"""Tiny .env loader (stdlib only). Imported at the top of entrypoints."""
import os


def load_env(path: str = None) -> None:
    """Load KEY=VALUE pairs from a .env file into os.environ if not already set.

    Silently no-ops if the file doesn't exist. Won't override variables that
    are already set in the environment (so prod/CI env vars take precedence).
    """
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(path):
        return
    try:
        with open(path, encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip()
                # Strip optional surrounding quotes
                if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
                    val = val[1:-1]
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception:
        # Never crash on a malformed .env — just continue
        pass


# Auto-load on import for convenience
load_env()
