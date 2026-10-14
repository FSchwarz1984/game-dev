class_name UiTheme
## The two font themes (the choice is pending the user's decision; GameState "font_theme"):
##   "pixel"  Fusion Pixel 12px Proportional, zh_hans forms (TakWolf, SIL OFL 1.1, v2024.05.12):
##            drawn on its 12 px grid without antialiasing, so every glyph pixel is one native
##            pixel scaled by the stage's integer factor.
##   "vector" Noto Serif CJK SC Regular, subset (SIL OFL 1.1): antialiased, rasterised at the
##            screen's resolution (canvas_items stretch), so it stays sharp at any scale.
## Sources and licences: art/fonts/SOURCES.txt and the OFL texts beside the fonts.

const FONTS := {
	"pixel": "res://art/fonts/fusion-pixel-12px-proportional-zh_hans.woff2",
	"vector": "res://art/fonts/noto-serif-sc-subset.woff2",
}
## Native-pixel sizes per role. The pixel font only has one true size (12) and its multiples.
const SIZES := {
	"pixel": {"body": 12, "name": 12, "small": 12, "card": 12, "title": 24},
	"vector": {"body": 11, "name": 11, "small": 9, "card": 13, "title": 26},
}
const LINE := {"pixel": 16, "vector": 16}

static var _fonts: Dictionary = {}


static func clear() -> void:
	_fonts.clear()


static func font(kind: String) -> Font:
	if _fonts.has(kind):
		return _fonts[kind]
	var f := load(FONTS.get(kind, FONTS["pixel"])) as FontFile
	if f == null:
		push_error("UiTheme: font for '%s' missing" % kind)
		return ThemeDB.fallback_font
	f = f.duplicate() as FontFile
	if kind == "pixel":
		f.antialiasing = TextServer.FONT_ANTIALIASING_NONE
		f.hinting = TextServer.HINTING_NONE
		f.subpixel_positioning = TextServer.SUBPIXEL_POSITIONING_DISABLED
		f.multichannel_signed_distance_field = false
	else:
		f.antialiasing = TextServer.FONT_ANTIALIASING_GRAY
		f.hinting = TextServer.HINTING_LIGHT
		f.subpixel_positioning = TextServer.SUBPIXEL_POSITIONING_AUTO
	_fonts[kind] = f
	return f


static func size(kind: String, role: String) -> int:
	return int(SIZES.get(kind, SIZES["pixel"]).get(role, 12))


static func make(kind: String) -> Theme:
	var t := Theme.new()
	t.default_font = font(kind)
	t.default_font_size = size(kind, "body")
	return t
