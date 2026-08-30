#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "${script_dir}/../.." && pwd)"
repo_dir="${project_root}/.benchmark-cache/LongMemEval"
data_dir="${project_root}/.benchmark-data/longmemeval-v1"
dataset_path="${data_dir}/longmemeval_s_cleaned.json"

source_repository="https://github.com/xiaowu0162/LongMemEval.git"
source_commit="9e0b455f4ef0e2ab8f2e582289761153549043fc"

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

if command -v python >/dev/null 2>&1; then
  python_bin="$(command -v python)"
elif [[ -x "${project_root}/.venv/bin/python" ]]; then
  python_bin="${project_root}/.venv/bin/python"
else
  python_bin="$(command -v python3)"
fi
PIP_INDEX_URL="https://pypi.org/simple" \
  "${python_bin}" -m pip install -e "${project_root}[dev]"
"${python_bin}" -m benchmarks.longmemeval_v1.prepare_dataset \
  --dataset-path "${dataset_path}"
sha256sum "${dataset_path}"
echo "LongMemEval commit: $(git -C "${repo_dir}" rev-parse HEAD)"
