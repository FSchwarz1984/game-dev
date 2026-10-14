class_name FieldEntity
extends RefCounted
## A thing in the field: an object, a creature or a person she can target. Pure data; the world
## draws it with an EntityView. Positions in metres on the ground plane; `h` is the height of the
## ground it stands on (filled in from the region when added).
##
## def keys (Field.add): id, kind, name, x, z, r, solid, priority, q, base, max, sacred, deep,
## targetable, reach, material, ctx {"label": Callable -> String, "run": Callable -> String}, data.

var id := ""
var kind := "thing"
var name := ""
var x := 0.0
var z := 0.0
var h := 0.0
var r := 0.5
var solid := false
var priority := 0
var deep := false
var targetable := true
var hidden := false
var reach := -1.0          # < 0: the field default (1.6 m + r)
var ctx: Dictionary = {}
var far := 0.0             # 0 near .. 1 far (遠化)
var data: Dictionary = {}
var holder: QualityHolder


## 遠化 in one rule: a thing is as far as the share of its natural qualities it has lost.
## A thing that lost everything (`deep`) cannot be reached at all.
func farness() -> float:
	if deep:
		return 1.0
	var lost := 0
	var natural := 0
	for k in Qualities.ALL:
		var b: int = holder.base[k]
		if b <= 0:
			continue
		natural += b
		lost += maxi(0, b - holder.q[k])
	return float(lost) / float(natural) if natural > 0 else 0.0


func context_label() -> String:
	if ctx.has("label") and ctx["label"] is Callable:
		return String((ctx["label"] as Callable).call())
	return ""


func pos() -> Vector2:
	return Vector2(x, z)
