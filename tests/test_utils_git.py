from sdlc.utils.git import git_commit, git_current_branch, git_diff, git_root, is_git_repo


def test_is_git_repo_non_git_dir(tmp_dir):
    assert is_git_repo(tmp_dir) is False


def test_git_root_non_git_dir(tmp_dir):
    assert git_root(tmp_dir) is None


def test_git_current_branch_non_git_dir(tmp_dir):
    assert git_current_branch(tmp_dir) is None


def test_git_diff_non_git_dir(tmp_dir):
    assert git_diff(tmp_dir) == ""


def test_git_diff_staged_non_git_dir(tmp_dir):
    assert git_diff(tmp_dir, staged=True) == ""


def test_git_commit_non_git_dir(tmp_dir):
    assert git_commit("test", tmp_dir) is False
