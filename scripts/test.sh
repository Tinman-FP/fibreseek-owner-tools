#!/bin/bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/fibreseek-owner-tools.XXXXXX")"
trap 'rm -rf "${tmp_dir}"' EXIT

ssh-keygen -q -t ed25519 -N '' -C 'fibreseek-owner-tools-test' \
  -f "${tmp_dir}/test_key"

python3 "${repo_root}/scripts/build_fibrepack.py" \
  --public-key "${tmp_dir}/test_key.pub" \
  --output-dir "${tmp_dir}/dist"

package="${tmp_dir}/dist/fibreseek-sk3-2.2.42.832.321.fibrepack"
python3 "${repo_root}/scripts/verify_fibrepack.py" \
  "${package}" \
  --public-key "${tmp_dir}/test_key.pub"

first_digest="$(shasum -a 256 "${package}" | awk '{print $1}')"
python3 "${repo_root}/scripts/build_fibrepack.py" \
  --public-key "${tmp_dir}/test_key.pub" \
  --output-dir "${tmp_dir}/dist"
second_digest="$(shasum -a 256 "${package}" | awk '{print $1}')"
test "${first_digest}" = "${second_digest}"

python3 -m py_compile \
  "${repo_root}/scripts/build_fibrepack.py" \
  "${repo_root}/scripts/verify_fibrepack.py"

echo "All tests passed."
