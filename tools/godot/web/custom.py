# W-1 (2026-10-14): the web target was dropped (native Windows + Android instead). Kept for
# reference only. No template was ever built with this profile, so treat it as an untested draft.
#
# SCons profile for the size-optimized Web export templates of this 2D game.
# Used by tools/godot/web/build-web-template.sh as `scons ... profile=tools/godot/web/custom.py`.
# Arguments given on the scons command line override the values here. Some must be given there:
# platform/target/optimize (platform/web/detect.py get_flags() overrides any of its keys that are
# not on the command line, e.g. it forces optimize=size) and lto (production=yes resets lto to the
# command-line value or "auto", which means thin LTO on the web). build-web-template.sh passes
# platform=web target=... production=yes optimize=size_extra lto=full.
#
# The game is 2D pixel art (480x270, Compatibility renderer / WebGL2), runs in a browser on desktop
# and phones, loads only resources imported by the editor (textures stored lossless, OGG/MP3 audio,
# TTF/OTF fonts), and does no networking. Everything below that a game like that never touches is
# compiled out to cut download size. Re-enable a line if the game starts to need it; the editor
# build (build-editor.sh) keeps every module, so only the exported game is affected.
# Size and text-server measurements: docs/knowledge/10-godot-toolchain.md.

import os

# --- Build-wide switches -------------------------------------------------------------------------
threads = "no"  # Single-threaded wasm: no SharedArrayBuffer, no COOP/COEP headers, no pthread workers.
use_closure_compiler = "yes"  # Minifies the Emscripten/Godot JS glue (needs Emscripten >= 4.0.11).
# CAUTION: disable_3d also removes WorldEnvironment (registered in the 3D section of
# scene/register_scene_types.cpp), so 2D glow/HDR tonemapping would be lost. Re-decide before use.
disable_3d = "yes"  # No 3D nodes or servers; also turns off 3D physics, 3D navigation and XR.
# JavaScriptBridge.eval() runs eval(); the game does not use it, and without it no engine code path
# can call eval() (blocked by a CSP without 'unsafe-eval'). get_interface()/create_callback() stay.
javascript_eval = "no"
# Kept on purpose: advanced GUI (disable_advanced_gui would remove RichTextLabel, RichTextEffect,
# SubViewportContainer, PopupMenu, OptionButton, TextEdit and VirtualJoystick), 2D physics
# (collisions, CharacterBody2D), and deprecated=yes (the editor keeps deprecated APIs, so a template
# without them would fail only at run time, on the web).
# Not used here: build_profile (class-level stripping); worth trying once the game is complete.

# ZIP archives (ZIPReader/ZIPPacker, loading .zip packs): the game ships one .pck.
minizip = "no"
# Brotli decoder: used for WOFF2 fonts and for the engine's built-in default font (OpenSans, stored
# as WOFF2). Without it that default font is empty, so the project MUST set its own default font
# (gui/theme/custom_font, or a theme); ship fonts as TTF/OTF.
brotli = "no"
# 2D navigation (NavigationServer2D, NavigationAgent2D, RVO avoidance, TileSet navigation layers).
# Carrying routes can use AStar2D / AStarGrid2D, which are in core and stay. Re-enable if
# NavigationAgent2D or crowd avoidance is wanted.
disable_navigation_2d = "yes"

# --- Text server ---------------------------------------------------------------------------------
# Exactly one is needed. Fallback (no HarfBuzz/ICU) is much smaller; Advanced adds HarfBuzz shaping,
# ICU line breaking (UAX #14, CJK and kinsoku) and OpenType features such as 'locl'.
# Choose with GODOT_TEXT_SERVER=fb|adv in the environment (default: fb, see knowledge/10).
_ts = os.environ.get("GODOT_TEXT_SERVER", "fb")
module_text_server_fb_enabled = "yes" if _ts == "fb" else "no"
module_text_server_adv_enabled = "yes" if _ts == "adv" else "no"
graphite = "no"  # SIL Graphite smart fonts (adv only): not needed for CJK or Latin.
del _ts, os  # Leftover names would be reported as unknown SCons variables.

# --- Modules kept (listed so the choice is explicit) ---------------------------------------------
module_gdscript_enabled = "yes"
module_freetype_enabled = "yes"  # Font rasterization for both text servers.
module_regex_enabled = "yes"
module_jpg_enabled = "yes"
module_webp_enabled = "yes"  # Lossless textures are imported as WebP by default (force_png=false).
module_ogg_enabled = "yes"
module_vorbis_enabled = "yes"
module_mp3_enabled = "yes"
module_noise_enabled = "yes"  # FastNoiseLite / NoiseTexture2D: small, useful for procedural detail.
module_interactive_music_enabled = "yes"  # AudioStreamInteractive/Playlist/Synchronized: small.
module_godot_physics_2d_enabled = "yes"

# --- Modules removed -----------------------------------------------------------------------------
# Image formats: textures are imported in the editor and stored as lossless WebP/PNG inside the
# .pck; the game never decodes these formats at run time.
module_bmp_enabled = "no"
module_tga_enabled = "no"
module_hdr_enabled = "no"
module_tinyexr_enabled = "no"
module_dds_enabled = "no"
module_ktx_enabled = "no"
# SVG (ThorVG): SVGs are rasterized at import time. Without it the default theme's icons
# (checkbox ticks, arrows) are blank 16x16 images; the game's UI uses its own pixel-art theme.
module_svg_enabled = "no"
# GPU texture compression codecs (VRAM-compressed import modes): pixel art is imported lossless.
module_basis_universal_enabled = "no"
module_astcenc_enabled = "no"
module_bcdec_enabled = "no"
module_etcpak_enabled = "no"
# MSDF font rendering: the pixel-art UI uses plain rasterized fonts.
module_msdfgen_enabled = "no"
# Video playback (Theora): no video in the game; cut-scenes are played in-engine.
module_theora_enabled = "no"
# Networking and multiplayer: the game is offline and single-player. On the web, HTTPRequest goes
# through the browser and does not need mbedTLS either.
module_mbedtls_enabled = "no"
module_enet_enabled = "no"
module_upnp_enabled = "no"
module_webrtc_enabled = "no"
module_websocket_enabled = "no"
module_multiplayer_enabled = "no"
module_jsonrpc_enabled = "no"
# Camera feeds (CameraServer): unused.
module_camera_enabled = "no"
# VisualShader graphs: shaders are written as text.
module_visual_shader_enabled = "no"
# 3D-only modules (most are also implied by disable_3d=yes; listed for clarity).
module_csg_enabled = "no"
module_gltf_enabled = "no"
module_fbx_enabled = "no"
module_gridmap_enabled = "no"
module_godot_physics_3d_enabled = "no"
module_jolt_physics_enabled = "no"
module_meshoptimizer_enabled = "no"
module_navigation_3d_enabled = "no"
module_vhacd_enabled = "no"
module_raycast_enabled = "no"
module_mobile_vr_enabled = "no"
module_openxr_enabled = "no"
module_webxr_enabled = "no"
