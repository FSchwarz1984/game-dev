# Shared settings for the Godot toolchain scripts in tools/godot/ (sourced, not run).
# Default path (2026-10-14): the OFFICIAL Godot 4.7.2-stable editor and export templates, fetched
# and SHA512-verified by setup-godot.sh. The source-build scripts (build-editor.sh,
# build-templates.sh) are a documented fallback for when we modify the engine; not used by default.
# Everything heavy lives outside the repo, under $GODOT_HOME (default /home/user/godotengine):
#   $GODOT_BIN            official editor binary (setup-godot.sh)
#   $GODOT_TEMPLATES_DIR  official export templates (~/.local/share/godot/export_templates/4.7.2.stable)
#   $ANDROID_HOME         Android SDK (setup-android-sdk.sh)
#   $GODOT_SRC, $GODOT_OUT  engine source clone and source-built binaries (fallback only)
# Override any of them from the environment.

GODOT_VERSION="${GODOT_VERSION:-4.7.2}"
GODOT_FLAVOR="${GODOT_FLAVOR:-stable}"
GODOT_TAG="${GODOT_TAG:-${GODOT_VERSION}-${GODOT_FLAVOR}}"
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
GODOT_BIN="${GODOT_BIN:-$GODOT_HOME/editor/Godot_v${GODOT_VERSION}-${GODOT_FLAVOR}_linux.x86_64}"
# Directory the editor searches for templates by their official names (version.py: 4.7.2 + "stable").
GODOT_TEMPLATES_DIR="${GODOT_TEMPLATES_DIR:-$HOME/.local/share/godot/export_templates/${GODOT_VERSION}.${GODOT_FLAVOR}}"
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

# The editor writes its Android SDK/JDK paths into its settings file the first time it starts, from
# ANDROID_HOME/JAVA_HOME if set or from a default (~/Android/Sdk). If that file already exists with
# other paths (e.g. the editor ran once before the SDK was set up), point it at ours.
godot_editor_settings_android() {
  local f="$HOME/.config/godot/editor_settings-${GODOT_VERSION%.*}.tres"
  [ -f "$f" ] || return 0
  python3 -I - "$f" "$ANDROID_HOME" "$JAVA_HOME" <<'PYEOF'
import re, sys
path, sdk, jdk = sys.argv[1:4]
s = open(path, encoding="utf-8").read()
for key, val in (("export/android/android_sdk_path", sdk), ("export/android/java_sdk_path", jdk)):
    line = f'{key} = "{val}"'
    if re.search(rf"^{re.escape(key)} = .*$", s, flags=re.M):
        s = re.sub(rf"^{re.escape(key)} = .*$", line, s, flags=re.M)
    else:
        s = s.rstrip("\n") + "\n" + line + "\n"
open(path, "w", encoding="utf-8").write(s)
PYEOF
}

# Prints "<bytes> (<MiB> MiB)" for a file.
size_of() {
  local b
  b="$(stat -c %s "$1")"
  printf '%s (%s MiB)' "$b" "$(awk -v b="$b" 'BEGIN { printf "%.2f", b / 1048576 }')"
}
