import os
import tempfile
import unittest
from pathlib import Path

from utils import langsmith_config


class LangSmithConfigTests(unittest.TestCase):
    def setUp(self):
        self.original_env = os.environ.copy()
        os.environ.pop("LANGCHAIN_TRACING_V2", None)
        os.environ.pop("LANGCHAIN_API_KEY", None)
        os.environ.pop("LANGCHAIN_PROJECT", None)
        os.environ.pop("LANGCHAIN_ENDPOINT", None)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_configure_sets_defaults_and_trims_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text(
                "LANGCHAIN_TRACING_V2=false\n"
                "LANGCHAIN_API_KEY=  abc123  \n"
                "LANGCHAIN_PROJECT=  loan_underwriting_chatbot  \n"
                "LANGCHAIN_ENDPOINT= https://example.test \n"
            )
            langsmith_config.configure_langsmith(env_path=env_path)

            self.assertEqual(os.getenv("LANGCHAIN_TRACING_V2"), "false")
            self.assertEqual(os.getenv("LANGCHAIN_API_KEY"), "abc123")
            self.assertEqual(os.getenv("LANGCHAIN_PROJECT"), "loan_underwriting_chatbot")
            self.assertEqual(os.getenv("LANGCHAIN_ENDPOINT"), "https://example.test")


if __name__ == "__main__":
    unittest.main()
