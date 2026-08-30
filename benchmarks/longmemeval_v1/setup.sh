#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "${script_dir}/../.." && pwd)"
repo_dir="${project_root}/.benchmark-cache/LongMemEval"
data_dir="${project_root}/.benchmark-data/longmemeval-v1"
dataset_path="${data_dir}/longmemeval_s_cleaned.json"
dataset_tmp="${dataset_path}.tmp"

source_repository="https://github.com/xiaowu0162/LongMemEval.git"
source_commit="9e0b455f4ef0e2ab8f2e582289761153549043fc"
dataset_url="https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/main/longmemeval_s_cleaned.json"
dataset_sha256="d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442"

cleanup_tmp() {
  if [[ -f "${dataset_tmp}" ]]; then
    rm "${dataset_tmp}"
  fi
}
trap cleanup_tmp EXIT

mkdir -p "$(dirname "${repo_dir}")" "${data_dir}"

if [[ -e "${repo_dir}" ]]; then
  if [[ ! -d "${repo_dir}/.git" ]]; then
    echo "error: ${repo_dir} exists but is not a Git repository" >&2
    exit 1
  fi
  actual_remote="$(git -C "${repo_dir}" remote get-url origin)"
  case "${actual_remote}" in
    https://github.com/xiaowu0162/LongMemEval|https://github.com/xiaowu0162/LongMemEval.git)
      ;;
    *)
      echo "error: LongMemEval origin is not the official repository: ${actual_remote}" >&2
      exit 1
      ;;
  esac
  if [[ -n "$(git -C "${repo_dir}" status --porcelain)" ]]; then
    echo "error: external LongMemEval clone has local modifications" >&2
    exit 1
  fi
else
  git clone "${source_repository}" "${repo_dir}"
fi

git -C "${repo_dir}" fetch --quiet origin "${source_commit}"
git -C "${repo_dir}" checkout --quiet --detach "${source_commit}"
if [[ "$(git -C "${repo_dir}" rev-parse HEAD)" != "${source_commit}" ]]; then
  echo "error: failed to pin LongMemEval at ${source_commit}" >&2
  exit 1
fi
if [[ -n "$(git -C "${repo_dir}" status --porcelain)" ]]; then
  echo "error: external LongMemEval clone is dirty after checkout" >&2
  exit 1
fi

if [[ -f "${dataset_path}" ]]; then
  actual_sha256="$(sha256sum "${dataset_path}" | awk '{print $1}')"
  if [[ "${actual_sha256}" != "${dataset_sha256}" ]]; then
    echo "error: dataset checksum changed: expected ${dataset_sha256}, got ${actual_sha256}" >&2
    exit 1
  fi
else
  curl --fail --location --retry 3 --output "${dataset_tmp}" "${dataset_url}"
  actual_sha256="$(sha256sum "${dataset_tmp}" | awk '{print $1}')"
  if [[ "${actual_sha256}" != "${dataset_sha256}" ]]; then
    echo "error: downloaded dataset checksum mismatch: expected ${dataset_sha256}, got ${actual_sha256}" >&2
    exit 1
  fi
  mv "${dataset_tmp}" "${dataset_path}"
fi

if command -v python >/dev/null 2>&1; then
  python_bin="$(command -v python)"
elif [[ -x "${project_root}/.venv/bin/python" ]]; then
  python_bin="${project_root}/.venv/bin/python"
else
  python_bin="$(command -v python3)"
fi
PIP_INDEX_URL="https://pypi.org/simple" \
  "${python_bin}" -m pip install -e "${project_root}[dev]"
sha256sum "${dataset_path}"
echo "LongMemEval commit: $(git -C "${repo_dir}" rev-parse HEAD)"
