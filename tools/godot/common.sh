# Shared settings for the Godot toolchain scripts in tools/godot/ (sourced, not run).
# Everything heavy lives outside the repo, under $GODOT_HOME (default /home/user/godotengine):
#   $GODOT_SRC   engine source, shallow clone of $GODOT_TAG
#   $EMSDK_DIR   Emscripten SDK (git clone of emscripten-core/emsdk)
#   $GODOT_OUT   built editor binary and packaged export templates
# Override any of them from the environment.

GODOT_TAG="${GODOT_TAG:-4.7.2-stable}"
# Commit the tag pointed to when the toolchain was set up (2026-10-14); a mismatch means the tag
# moved or the clone is something else, and the scripts stop instead of building it.
GODOT_COMMIT="${GODOT_COMMIT:-ed1daf0bf001b61586d9930840f2f1394092c079}"
GODOT_REPO="${GODOT_REPO:-https://github.com/godotengine/godot}"
# Emscripten version pinned by this tag's CI (.github/workflows/web_builds.yml, EM_VERSION).
# The tag's platform/web/detect.py requires >= 4.0.0; closure compiler needs >= 4.0.11.
EM_VERSION="${EM_VERSION:-4.0.11}"

GODOT_HOME="${GODOT_HOME:-/home/user/godotengine}"
GODOT_SRC="${GODOT_SRC:-$GODOT_HOME/godot}"
EMSDK_DIR="${EMSDK_DIR:-$GODOT_HOME/emsdk}"
GODOT_OUT="${GODOT_OUT:-$GODOT_HOME/out}"
GODOT_BIN="${GODOT_BIN:-$GODOT_OUT/godot-editor}"
# Directory the editor searches for official-style templates (version.py: 4.7.2 + "stable").
GODOT_TEMPLATES_DIR="${GODOT_TEMPLATES_DIR:-$HOME/.local/share/godot/export_templates/${GODOT_TAG%-stable}.stable}"
JOBS="${JOBS:-$(nproc)}"
# Android: the editor takes its defaults for export/android/android_sdk_path and java_sdk_path
# from these when it first creates its settings (~/.config/godot/editor_settings-4.7.tres).
export ANDROID_HOME="${ANDROID_HOME:-$GODOT_HOME/android-sdk}"
export JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java-21-openjdk-amd64}"

TOOLS_GODOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log() { printf '[godot-toolchain] %s\n' "$*" >&2; }

# Shallow-clones $GODOT_TAG once. An existing clone is only checked, never deleted or re-cloned:
# it must point at $GODOT_REPO and sit on $GODOT_COMMIT.
godot_fetch_source() {
  if [ -d "$GODOT_SRC/.git" ]; then
    local head url
    head="$(git -C "$GODOT_SRC" rev-parse HEAD)"
    url="$(git -C "$GODOT_SRC" remote get-url origin)"
    if [ "$head" != "$GODOT_COMMIT" ] || [ "${url%.git}" != "${GODOT_REPO%.git}" ]; then
      log "existing clone at $GODOT_SRC is $url @ $head, expected $GODOT_REPO @ $GODOT_COMMIT"
      log "refusing to touch it; move it away or set GODOT_SRC"
      return 1
    fi
    log "source ok: $GODOT_SRC @ $GODOT_TAG ($head)"
    return 0
  fi
  if [ -e "$GODOT_SRC" ]; then
    log "$GODOT_SRC exists but is not a git clone; refusing to touch it"
    return 1
  fi
  mkdir -p "$(dirname "$GODOT_SRC")"
  log "cloning $GODOT_REPO @ $GODOT_TAG (shallow; can look stalled while unpacking, do not interrupt)"
  GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 --branch "$GODOT_TAG" "$GODOT_REPO" "$GODOT_SRC"
  local head
  head="$(git -C "$GODOT_SRC" rev-parse HEAD)"
  if [ "$head" != "$GODOT_COMMIT" ]; then
    log "WARNING: $GODOT_TAG now resolves to $head, not $GODOT_COMMIT; check the tag before trusting the build"
  fi
}

# SCons is the only Python dependency of the engine build.
ensure_scons() {
  command -v scons >/dev/null 2>&1 || python3 -m pip install --quiet scons
}

# Prints "<bytes> (<MiB> MiB)" for a file.
size_of() {
  local b
  b="$(stat -c %s "$1")"
  printf '%s (%s MiB)' "$b" "$(awk -v b="$b" 'BEGIN { printf "%.2f", b / 1048576 }')"
}
