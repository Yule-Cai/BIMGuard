try:
    import ifcopenshell
    import ifcopenshell.util.element
    import ifcopenshell.util.unit
    HAS_IFC = True
except Exception:
    HAS_IFC = False
    ifcopenshell = None

HK_RULE = "HK Code of Practice for Fire Safety in Buildings 2011 (2024 Ed.) Table B2"


def _project_length_to_mm(model, value):
    """Convert a length expressed in IFC project units to millimetres.

    Real IFC files declare project units through IfcUnitAssignment. IfcOpenShell's
    calculate_unit_scale() returns the multiplier from project length units to SI
    metres, so this works for metre-, millimetre-, centimetre-, and imperial-based
    projects without guessing from the magnitude of the number.

    The regex fallback model is intentionally limited to BIMGuard's synthetic demo,
    whose generator writes lengths in metres; that path therefore uses x1000.
    """
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None

    if isinstance(model, dict) and model.get("_fallback"):
        return numeric * 1000.0

    if HAS_IFC:
        try:
            unit_scale = ifcopenshell.util.unit.calculate_unit_scale(model)
            return numeric * float(unit_scale) * 1000.0
        except Exception:
            # Do not silently infer real IFC units from the numeric magnitude.
            return None
    return None


def check_door_width(model, min_width_mm: float = 750.0):
    """Check the minimum individual exit-door-width component of HK FS Table B2.

    Returns dictionaries containing the measured width, threshold, delta, status,
    and rule citation. The geometric/regulatory decision is deterministic; an LLM
    may explain the evidence later but does not decide compliance.
    """
    results = []
    if model is None:
        return results

    if isinstance(model, dict) and model.get("_fallback"):
        doors = [e for e in model.get("elements", []) if e.is_a() == "IfcDoor"]
    else:
        try:
            doors = model.by_type("IfcDoor")
        except Exception:
            doors = []

    for d in doors:
        guid = getattr(d, "GlobalId", "")
        name = getattr(d, "Name", "") or getattr(d, "Tag", "") or "Unnamed Door"
        tag = getattr(d, "Tag", "") or ""

        width = getattr(d, "OverallWidth", None)
        width_source = "IfcDoor.OverallWidth" if width is not None else None

        if width is None and HAS_IFC and not isinstance(model, dict):
            try:
                psets = ifcopenshell.util.element.get_psets(d)
                qto = psets.get("Qto_DoorBaseQuantities", {})
                width = qto.get("OverallWidth") or qto.get("Width")
                if width is not None:
                    width_source = "Qto_DoorBaseQuantities"
                else:
                    for pset_name, ps in psets.items():
                        if isinstance(ps, dict) and "Width" in ps:
                            width = ps["Width"]
                            width_source = f"{pset_name}.Width"
                            break
            except Exception:
                pass

        if width is None:
            results.append({
                "guid": guid,
                "name": name,
                "tag": tag,
                "measured_mm": None,
                "required_mm": min_width_mm,
                "delta_mm": None,
                "status": "unknown",
                "rule": HK_RULE,
                "reason": "No IfcDoor.OverallWidth / door width quantity found",
                "type": "IfcDoor",
            })
            continue

        w_mm = _project_length_to_mm(model, width)
        if w_mm is None:
            results.append({
                "guid": guid,
                "name": name,
                "tag": tag,
                "measured_mm": None,
                "required_mm": min_width_mm,
                "delta_mm": None,
                "status": "unknown",
                "rule": HK_RULE,
                "reason": "Door width found but IFC project length unit could not be resolved",
                "width_source": width_source,
                "type": "IfcDoor",
            })
            continue

        delta = round(w_mm - min_width_mm, 1)
        status = "pass" if w_mm >= min_width_mm else "fail"
        results.append({
            "guid": guid,
            "name": name,
            "tag": tag,
            "measured_mm": round(w_mm, 1),
            "required_mm": min_width_mm,
            "delta_mm": delta,
            "status": status,
            "rule": HK_RULE,
            "width_source": width_source,
            "type": "IfcDoor",
        })
    return results


def summarize_door_results(results):
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "pass")
    failed = sum(1 for r in results if r["status"] == "fail")
    unknown = total - passed - failed
    return {"total": total, "passed": passed, "failed": failed, "unknown": unknown}
