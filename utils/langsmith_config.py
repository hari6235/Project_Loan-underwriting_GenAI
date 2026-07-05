import os
from pathlib import Path
from typing import Optional, Union

from dotenv import load_dotenv


def configure_langsmith(env_path: Optional[Union[str, os.PathLike]] = None) -> None:
    """Load LangSmith-related environment variables from the project .env file.

    This is intentionally executed before creating LangChain/OpenAI clients so
    that tracing is configured consistently across app entry points.
    """
    project_root = Path(__file__).resolve().parents[1]
    resolved_path = Path(env_path) if env_path else project_root / ".env"
    load_dotenv(dotenv_path=resolved_path, override=False)

    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")

    for key in ("LANGCHAIN_API_KEY", "LANGCHAIN_PROJECT", "LANGCHAIN_TRACING_V2", "LANGCHAIN_ENDPOINT"):
        value = os.getenv(key)
        if value is not None:
            os.environ[key] = value.strip()
