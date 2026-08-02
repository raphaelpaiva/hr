#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

if [ ! -x venv/bin/cz ]; then
  echo "commitizen não instalado. Instale requirements-dev.txt primeiro." >&2
  exit 1
fi

if [ "$DRY_RUN" -eq 1 ]; then
  venv/bin/cz bump --changelog --files-only
else
  venv/bin/cz bump --changelog
fi

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
COMMIT="$(git rev-parse --short HEAD)"
if [ "$DRY_RUN" -eq 1 ]; then
  TAG="v$(venv/bin/python -c "import re, pathlib; print(re.search(r'version = \"([^\"]+)\"', pathlib.Path('pyproject.toml').read_text()).group(1))")"
else
  TAG="$(git describe --tags --exact-match HEAD 2>/dev/null || echo '')"
fi

cat > src/app/git_info.py <<EOF
BRANCH = "${BRANCH}"
COMMIT = "${COMMIT}"
TAG = "${TAG}"
EOF

if [ "$DRY_RUN" -eq 1 ]; then
  echo
  echo "modo dry-run: arquivos atualizados, nenhum git add/commit/push executado."
  git status --short
  exit 0
fi

git add src/app/git_info.py
git commit -m "chore: atualiza git info"
git push origin HEAD --follow-tags
