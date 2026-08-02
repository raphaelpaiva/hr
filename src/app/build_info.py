from app import version

try:
  from app import git_info
  BRANCH = git_info.BRANCH
  COMMIT = git_info.COMMIT
  TAG = git_info.TAG
except (ImportError, AttributeError):
  BRANCH = ""
  COMMIT = ""
  TAG = ""


def get_build_info() -> dict:
  return {
    "version": version.__version__,
    "branch": BRANCH,
    "commit": COMMIT,
    "tag": TAG,
  }
