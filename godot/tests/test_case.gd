class_name TestCase
extends RefCounted
## Base class of the headless unit tests (tests/run.gd). Every method named test_* is a test; it may
## await (the runner awaits it). Checks record failures and let the test continue, like node:test's
## assert would not, so one run reports every broken expectation.

var failures: Array[String] = []
var current := ""
var checks := 0


func check(cond: bool, msg: String = "") -> bool:
	checks += 1
	if not cond:
		failures.append("%s: %s" % [current, msg if msg != "" else "check failed"])
	return cond


func eq(a, b, msg: String = "") -> bool:
	return check(_same(a, b), "%sexpected %s, got %s" % [(msg + ": ") if msg != "" else "", var_to_str(b), var_to_str(a)])


func ne(a, b, msg: String = "") -> bool:
	return check(not _same(a, b), "%sexpected something other than %s" % [(msg + ": ") if msg != "" else "", var_to_str(b)])


func near(a: float, b: float, eps: float = 1e-6, msg: String = "") -> bool:
	return check(absf(a - b) <= eps, "%sexpected %.6f +- %s, got %.6f" % [(msg + ": ") if msg != "" else "", b, str(eps), a])


static func _same(a, b) -> bool:
	if typeof(a) != typeof(b):
		if (typeof(a) == TYPE_INT or typeof(a) == TYPE_FLOAT) and (typeof(b) == TYPE_INT or typeof(b) == TYPE_FLOAT):
			return float(a) == float(b)
		return false
	return a == b


## Load the shared body rules and return one profile ("legacy" matches the JS tests' body).
static func profile(name: String) -> Dictionary:
	var rules := load("res://systems/body_rules.tres") as BodyRules
	return rules.profile(name)
