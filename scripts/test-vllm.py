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
    """GET {base_url}/models from a local vLLM (OpenAI-compatible) server."""
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

    base_url = os.getenv("VLLM_BASE_URL", "http://127.0.0.1:8000/v1").rstrip("/")
    model_name = os.getenv("VLLM_MODEL", "Qwen/Qwen3-Coder-Next-FP8")
    api_key = os.getenv("VLLM_API_KEY", "test")

    os.environ.setdefault("OPENAI_BASE_URL", base_url)
    os.environ.setdefault("OPENAI_API_KEY", api_key)

    try:
        catalog = fetch_catalog(base_url, api_key)
    except urllib.error.URLError as exc:
        raise SystemExit(
            f"Could not reach vLLM at {base_url}: {exc}\n"
            "Start the local server first, e.g.:\n"
            "  ~/Desktop/start-vllm.sh              # or\n"
            "  ~/Desktop/serve-local-llm.sh up coder-next"
        ) from exc

    models = catalog_model_ids(catalog)
    print("vllm models:", ", ".join(sorted(models)) or "<none>")
    if model_name not in models:
        raise SystemExit(
            f"vLLM model {model_name!r} is not in the catalog. "
            f"Pick one of the models listed above, or start the matching recipe "
            f"(e.g. ~/Desktop/serve-local-llm.sh up coder-next)."
        )

    if os.getenv("VLLM_SKIP_INVOKE", "false").strip().lower() in {"1", "true", "yes"}:
        print(
            f"vllm model {model_name!r} present in catalog; "
            "skipping invoke (VLLM_SKIP_INVOKE)."
        )
        raise SystemExit(0)

    from deepagents_code.config import create_model

    model = create_model(f"openai:{model_name}").model
    print(type(model))
    print(f"vllm: invoking {model_name!r}...")
    response = model.invoke("Reply with only the word OK.")
    # On langchain 1.x, message content may be a list of content blocks
    # (dicts with a "text" field) rather than a plain string.
    content = response.content
    if isinstance(content, list):
        text = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    else:
        text = content
    print("vllm chat:", text.strip())


if __name__ == "__main__":
    main()
