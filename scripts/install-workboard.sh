#!/usr/bin/env bash
# Installs the CCR Workboard skill and rules.
#
#   scripts/install-workboard.sh                 for every Claude Code session of this user
#                                                (~/.claude/skills/workboard and ~/.claude/CLAUDE.md)
#   scripts/install-workboard.sh --repo <path>   also into a repository
#                                                (<path>/.claude/skills/workboard and <path>/CLAUDE.md)
#
# Safe to run again: the rules sit between workboard markers in CLAUDE.md and are replaced,
# not duplicated. Nothing else in CLAUDE.md is changed.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
skill_src="$here/.claude/skills/workboard/SKILL.md"
rules_src="$here/.claude/workboard-rules.md"
claude_home="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
begin='<!-- workboard:begin -->'
end='<!-- workboard:end -->'

for f in "$skill_src" "$rules_src"; do
  [ -f "$f" ] || { echo "Missing $f" >&2; exit 1; }
done

copy_skill() {  # $1 = .claude directory to install into
  local dst="$1/skills/workboard/SKILL.md"
  mkdir -p "$(dirname "$dst")"
  if [ "$skill_src" -ef "$dst" ]; then return; fi
  cp "$skill_src" "$dst"
  echo "Skill:  $dst"
}

write_rules() {  # $1 = CLAUDE.md to update
  local file="$1" tmp
  mkdir -p "$(dirname "$file")"
  touch "$file"
  tmp="$(mktemp)"
  # Keep everything outside the markers, minus trailing blank lines.
  awk -v b="$begin" -v e="$end" '
    $0 == b { skip = 1; next }
    $0 == e { skip = 0; next }
    skip    { next }
            { lines[++n] = $0; if ($0 ~ /[^[:space:]]/) last = n }
    END     { for (i = 1; i <= last; i++) print lines[i] }
  ' "$file" > "$tmp"
  {
    cat "$tmp"
    if [ -s "$tmp" ]; then echo; fi
    echo "$begin"
    cat "$rules_src"
    echo "$end"
  } > "$file"
  rm -f "$tmp"
  echo "Rules:  $file"
}

repo=""
while [ $# -gt 0 ]; do
  case "$1" in
    --repo) repo="${2:?--repo needs a path}"; shift 2 ;;
    -h|--help) sed -n '2,11p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

copy_skill "$claude_home"
write_rules "$claude_home/CLAUDE.md"

if [ -n "$repo" ]; then
  repo="$(cd "$repo" && pwd)"
  copy_skill "$repo/.claude"
  write_rules "$repo/CLAUDE.md"
fi

echo "Done. New Claude Code sessions pick this up when they start; a session that is already running needs to be told to read the skill."
