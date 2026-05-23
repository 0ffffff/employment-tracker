#!/usr/bin/env bash
# Install the Track CLI via uv, put `track` on PATH, and enable Click subcommand tab completion.
#
# Usage (from a clone):
#   ./install.sh
#
# Usage (pipe install):
#   curl -fsSL https://0ffffff.github.io/install.sh | bash
#
# Environment:
#   TRACK_INSTALL_REPO   Git URL to clone for pipe install (default: 0ffffff/employment-tracker)
#   TRACK_INSTALL_BRANCH Branch to clone (default: main)
#   TRACK_INSTALL_SKIP_COMPLETION  Set to 1 to skip shell rc changes

set -euo pipefail

TOOL_NAME="employment-tracker"
COMPLETION_BEGIN="# >>> track shell completion (install.sh) >>>"
COMPLETION_END="# <<< track shell completion (install.sh) <<<"
INSTALL_BRANCH="${TRACK_INSTALL_BRANCH:-main}"
DEFAULT_INSTALL_REPO="https://github.com/0ffffff/employment-tracker.git"
TRACK_INSTALL_REPO="https://github.com/0ffffff/employment-tracker.git"

log() { printf '%s\n' "$*"; }
warn() { printf 'warning: %s\n' "$*" >&2; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

cleanup() {
  if [[ -n "${WORK_DIR:-}" && -d "${WORK_DIR:-}" ]]; then
    rm -rf "$WORK_DIR"
  fi
}

# True when this script is piped (curl | bash) rather than executed as a file.
is_piped_invocation() {
  local src="${BASH_SOURCE[0]:-}"
  [[ "$src" == "bash" || "$src" == "sh" || "$src" == "-" || "$src" == "/dev/stdin" ]]
}

resolve_repo_root() {
  local src="${BASH_SOURCE[0]:-}"
  local dir
  if is_piped_invocation; then
    return 1
  fi
  dir="$(cd "$(dirname "$src")" && pwd)" || return 1
  if [[ -f "$dir/pyproject.toml" ]]; then
    printf '%s' "$dir"
    return 0
  fi
  return 1
}

ensure_uv() {
  if command -v uv >/dev/null 2>&1; then
    return 0
  fi
  log "uv not found; installing via https://astral.sh/uv/install.sh"
  curl -fsSL https://astral.sh/uv/install.sh | sh
  export PATH="${HOME}/.local/bin:${PATH}"
  command -v uv >/dev/null 2>&1 || die "uv install failed; add ~/.local/bin to PATH and retry"
}

ensure_path() {
  export PATH="${HOME}/.local/bin:${PATH}"
  uv tool update-shell >/dev/null 2>&1 || true
}

install_tool() {
  local source_dir="$1"
  log "Installing ${TOOL_NAME} from ${source_dir}"
  # --reinstall rebuilds the wheel; --force alone can leave a stale 0.1.0 install cached.
  uv tool install --force --reinstall "$source_dir"
}

verify_track() {
  command -v track >/dev/null 2>&1 || die "'track' not on PATH after install; open a new shell or run: export PATH=\"\${HOME}/.local/bin:\${PATH}\""
  track --help >/dev/null 2>&1 || die "'track --help' failed"
  log "Installed: $(command -v track)"
}

shell_rc_file() {
  case "$(basename "${SHELL:-}")" in
    zsh) printf '%s' "${ZDOTDIR:-$HOME}/.zshrc" ;;
    bash) printf '%s' "$HOME/.bashrc" ;;
    *) return 1 ;;
  esac
}

completion_eval_line() {
  case "$(basename "${SHELL:-}")" in
    zsh) printf '%s' 'eval "$(_TRACK_COMPLETE=zsh_source track)"' ;;
    bash) printf '%s' 'eval "$(_TRACK_COMPLETE=bash_source track)"' ;;
    *) return 1 ;;
  esac
}

install_completion() {
  if [[ "${TRACK_INSTALL_SKIP_COMPLETION:-0}" == "1" ]]; then
    log "Skipping shell completion (TRACK_INSTALL_SKIP_COMPLETION=1)"
    return 0
  fi

  local rc line
  rc="$(shell_rc_file)" || {
    warn "Unsupported shell '${SHELL:-unknown}'; skip tab completion setup"
    return 0
  }

  if [[ "$(basename "${SHELL:-}")" == "bash" ]]; then
    local bash_version="${BASH_VERSION%%.*}"
    if [[ "${bash_version:-0}" -lt 4 ]]; then
      warn "macOS system bash is too old for Click completion (need 4.4+); use zsh or install a newer bash"
      return 0
    fi
  fi

  line="$(completion_eval_line)" || return 0

  if [[ -f "$rc" ]] && grep -qF "$COMPLETION_BEGIN" "$rc"; then
    log "Shell completion already configured in ${rc}"
    return 0
  fi

  mkdir -p "$(dirname "$rc")"
  touch "$rc"
  {
    printf '\n%s\n' "$COMPLETION_BEGIN"
    printf '%s\n' "$line"
    printf '%s\n' "$COMPLETION_END"
  } >>"$rc"
  log "Added tab completion to ${rc}"
}

main() {
  local repo_root source_dir

  ensure_uv
  ensure_path

  if repo_root="$(resolve_repo_root)"; then
    source_dir="$repo_root"
    log "Using checkout at ${source_dir}"
  else
    WORK_DIR="$(mktemp -d 2>/dev/null || mktemp -d -t track-install)"
    trap cleanup EXIT
    log "Cloning ${TRACK_INSTALL_REPO} (branch ${INSTALL_BRANCH})"
    git clone --depth 1 --branch "$INSTALL_BRANCH" "$TRACK_INSTALL_REPO" "$WORK_DIR"
    source_dir="$WORK_DIR"
  fi

  install_tool "$source_dir"
  verify_track
  install_completion

  log ""
  log "Done. Run: track --help"
}

main "$@"
