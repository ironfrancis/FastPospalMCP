#!/usr/bin/env bash
# 将本地 .env 与 SSH 私钥同步到 GitHub Actions Secrets（不打印 secret 值）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"

if ! command -v gh >/dev/null 2>&1; then
  echo "需要安装 GitHub CLI：brew install gh" >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "请先 gh auth login" >&2
  exit 1
fi

if [[ ! -f "${ROOT}/.env" ]]; then
  echo "缺少 ${ROOT}/.env" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
source "${ROOT}/.env"
set +a

SSH_KEY_FILE="${DEPLOY_SSH_KEY_FILE:-${HOME}/.ssh/id_rsa}"
if [[ ! -f "${SSH_KEY_FILE}" ]]; then
  echo "找不到 SSH 私钥：${SSH_KEY_FILE}（可用 DEPLOY_SSH_KEY_FILE 覆盖）" >&2
  exit 1
fi

required_app=(POSPAL_ACCOUNT POSPAL_PASSWORD MCP_AUTH_TOKEN)
for key in "${required_app[@]}"; do
  if [[ -z "${!key:-}" ]]; then
    echo "缺少 .env 键：${key}" >&2
    exit 1
  fi
done

if [[ -z "${DEPLOY_HOST:-}" ]]; then
  echo "缺少 .env 键：DEPLOY_HOST" >&2
  exit 1
fi

# Prefer git origin (handles repo renames / gh vs git URL mismatch)
ORIGIN_URL="$(git remote get-url origin 2>/dev/null || true)"
if [[ "${ORIGIN_URL}" =~ github.com[:/]([^/]+)/([^/.]+)(\.git)?$ ]]; then
  REPO="${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
else
  REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
fi
echo "==> 同步 Secrets 到 ${REPO}"
echo "    SSH key file: ${SSH_KEY_FILE}"

set_secret() {
  local name="$1"
  local value="$2"
  if [[ -z "${value}" ]]; then
    echo "跳过空值：${name}"
    return 0
  fi
  printf '%s' "${value}" | gh secret set "${name}" --repo "${REPO}"
  echo "  set ${name}"
}

set_secret DEPLOY_HOST "${DEPLOY_HOST}"
set_secret DEPLOY_USER "${DEPLOY_USER:-root}"
set_secret REMOTE_DIR "${REMOTE_DIR:-/opt/FastPospal}"
set_secret POSPAL_ACCOUNT "${POSPAL_ACCOUNT}"
set_secret POSPAL_PASSWORD "${POSPAL_PASSWORD}"
set_secret MCP_AUTH_TOKEN "${MCP_AUTH_TOKEN}"
set_secret FASTMCP_HTTP_ALLOWED_HOSTS "${FASTMCP_HTTP_ALLOWED_HOSTS:-[\"mmsd.site\"]}"

gh secret set DEPLOY_SSH_KEY --repo "${REPO}" < "${SSH_KEY_FILE}"
echo "  set DEPLOY_SSH_KEY"

echo "==> 完成。可用：gh secret list --repo ${REPO}"
