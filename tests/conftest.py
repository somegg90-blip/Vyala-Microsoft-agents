"""
pytest conftest — add project root to path and mock Azure SDK 
so tests run without credentials.
"""
import sys
import os
from unittest.mock import MagicMock

# 1. ADD PROJECT ROOT TO PATH (Fixes the ModuleNotFoundError)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# 2. Mock the entire azure namespace before any project imports
azure_mock = MagicMock()
sys.modules["azure"] = azure_mock
sys.modules["azure.identity"] = azure_mock.identity
sys.modules["azure.ai"] = azure_mock.ai
sys.modules["azure.ai.projects"] = azure_mock.ai.projects
sys.modules["azure.ai.projects.models"] = azure_mock.ai.projects.models
sys.modules["azure.ai.agents"] = azure_mock.ai.agents
sys.modules["azure.ai.agents.models"] = azure_mock.ai.agents.models

# 3. Set required env vars so module-level os.environ[] calls don't crash
os.environ.setdefault("FOUNDRY_PROJECT_ENDPOINT", "https://mock.azure.com")
os.environ.setdefault("AZURE_SEARCH_ENDPOINT", "https://mock.search.azure.com")
os.environ.setdefault("CONFIDENCE_THRESHOLD", "0.70")

# 4. Provide real enum-like values tests depend on
azure_mock.ai.agents.models.MessageRole.USER = "user"
azure_mock.ai.agents.models.MessageRole.ASSISTANT = "assistant"
azure_mock.ai.agents.models.ListSortOrder.DESCENDING = "desc"