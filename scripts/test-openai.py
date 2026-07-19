from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path


def load_env(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'").strip('"'))


def fetch_catalog(base_url: str, api_key: str, timeout: float = 10) -> dict:
    """GET {base_url}/models from an OpenAI-compatible server."""
    request = urllib.request.Request(
        f"{base_url}/models",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def catalog_model_ids(catalog: dict) -> set[str]:
    """Extract the set of model ids from an OpenAI-style /models payload."""
    return {item.get("id") for item in catalog.get("data", []) if item.get("id")}


def main() -> None:
    load_env(Path(__file__).resolve().parents[1] / ".env")

    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model_name = os.getenv("OPENAI_MODEL", "gpt-5.5")
    api_key = os.getenv("OPENAI_API_KEY", "")

    if not api_key:
        raise SystemExit(
            "OPENAI_API_KEY is not set; set it in .env to smoke-test the openai provider."
        )

    os.environ.setdefault("OPENAI_BASE_URL", base_url)

    try:
        catalog = fetch_catalog(base_url, api_key)
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not reach OpenAI endpoint at {base_url}: {exc}") from exc

    models = catalog_model_ids(catalog)
    print("openai models:", ", ".join(sorted(models)[:20]) or "<none>")
    if models and model_name not in models:
        print(
            f"warning: model {model_name!r} not listed by {base_url}/models "
            "(it may still be usable)."
        )

    if os.getenv("OPENAI_SKIP_INVOKE", "false").strip().lower() in {"1", "true", "yes"}:
        print("openai endpoint reachable; skipping invoke (OPENAI_SKIP_INVOKE).")
        raise SystemExit(0)

    from deepagents_code.config import create_model

    model = create_model(f"openai:{model_name}").model
    print(type(model))
    print(f"openai: invoking {model_name!r}...")
    response = model.invoke("Reply with only the word OK.")
    content = response.content
    if isinstance(content, list):
        text = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    else:
        text = content
    print("openai chat:", text.strip())


if __name__ == "__main__":
    main()
