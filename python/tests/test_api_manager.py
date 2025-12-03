import pytest
from unittest.mock import Mock, patch
from iskra.api.manager import IskraManager, RepoStatus


class TestIskraManager:

    def test_init(self):
        manager = IskraManager()
        assert manager.config_manager is not None

    def test_get_all_repos(self):
        manager = IskraManager()
        repos = manager.get_all_repos()
        assert isinstance(repos, list)

    @patch("iskra.api.manager.get_current_branch")
    @patch("iskra.api.manager.git_status_porcelain")
    def test_get_repo_status(self, mock_status, mock_branch):
        mock_branch.return_value = "main"
        mock_status.return_value = ""

        manager = IskraManager()
        status = manager.get_repo_status("/tmp/test")

        assert isinstance(status, RepoStatus)
        assert status.branch == "main"

    def test_filter_repos_by_pattern(self):
        manager = IskraManager()
        repos = manager.filter_repos(pattern="test*")
        assert isinstance(repos, list)

    @patch("iskra.api.manager.git_pull")
    def test_pull_repo(self, mock_pull):
        mock_pull.return_value = Mock(stdout="Already up to date.")

        manager = IskraManager()
        result = manager.pull_repo("/tmp/test")

        assert result.success
