#!/bin/bash
# Lints Swift source to ensure all Text views apply .applyTextScale().
set -e

errors=""

# Search for lines starting a Text initializer; allow multi-line constructs.
grep -nE '\bText\s*\(\s*(verbatim|localized|attributedString)?|Text\s*\(\s*Image\(' -R nfprogress \
  --include='*.swift' \
  --exclude-dir='*Tests' \
  --exclude-dir='Resources' \
  --exclude-dir='.build' \
  --exclude='*Generated*' \
  --exclude='*Preview.swift' | while IFS=: read -r file lineno _; do
  start=$lineno
  end=$((lineno+10))
  window=$(sed -n "${start},${end}p" "$file")
  if ! echo "$window" | grep -q 'applyTextScale'; then
    if echo "$window" | grep -q 'TODO: ignore-lint'; then
      yellow=$(tput setaf 3 || true)
      reset=$(tput sgr0 || true)
      echo "${yellow}Warning: ignoring lint for $file:$lineno${reset}" >&2
    else
      errors+="$file:$lineno Text without applyTextScale\n"
    fi
  fi
done

if [[ -n "$errors" ]]; then
  echo -e "$errors"
  exit 1
else
  echo "All Text views use applyTextScale"
fi
