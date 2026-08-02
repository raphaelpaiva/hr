import re
from pathlib import Path

from app import version
from app import git_info
from app.build_info import get_build_info

ROOT = Path(__file__).resolve().parent.parent


def test_version_matches_pyproject():
  pyproject = (ROOT / 'pyproject.toml').read_text()
  match = re.search(r'\[tool\.commitizen\]\n(?:.*\n)*?version = "([^"]+)"', pyproject)
  assert match, 'pyproject.toml must declare [tool.commitizen] version'
  assert version.__version__ == match.group(1)


def test_git_info_exposes_expected_attributes():
  for attr in ('BRANCH', 'COMMIT', 'TAG'):
    assert isinstance(getattr(git_info, attr), str)


def test_get_build_info_structure():
  info = get_build_info()
  assert set(info.keys()) == {'version', 'branch', 'commit', 'tag'}
  assert info['version'] == version.__version__


def test_meta_endpoint(client):
  res = client.get('/api/v1/meta')
  assert res.status_code == 200
  assert set(res.json().keys()) == {'version', 'branch', 'commit', 'tag'}
