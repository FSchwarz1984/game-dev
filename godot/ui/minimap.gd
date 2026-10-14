class_name Minimap
extends RefCounted
## Minimap INTERFACE STUB (F-1: a minimap may exist, but areas unlock only when conditions are met;
## how they unlock is pending the user's decision, godot-plan R-2). No drawing, no content: only the
## API the world and the save use, so P3 can add the map without touching callers.
##   register_area(id, {"region": id, "rect_m": Rect2, "label": String})
##   reveal(id, why)  -> true when it was hidden;  is_revealed(id);  revealed_ids()
##   to_save() / from_save(dict)
## Signal area_revealed(id, why): the HUD may later show the newly revealed piece on the map itself
## (never a centre-screen notice: F-1).

signal area_revealed(id: String, why: String)

var areas: Dictionary = {}
var revealed: Dictionary = {}


func register_area(id: String, def: Dictionary) -> void:
	areas[id] = def


func reveal(id: String, why: String = "") -> bool:
	if not areas.has(id) or revealed.has(id):
		return false
	revealed[id] = {"why": why, "at_unix": Time.get_unix_time_from_system()}
	area_revealed.emit(id, why)
	return true


func is_revealed(id: String) -> bool:
	return revealed.has(id)


func revealed_ids() -> Array:
	return revealed.keys()


func to_save() -> Dictionary:
	return {"revealed": revealed.duplicate(true)}


func from_save(d: Dictionary) -> void:
	revealed = d.get("revealed", {}).duplicate(true)
