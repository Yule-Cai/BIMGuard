try:
    import ifcopenshell
    import ifcopenshell.util.element
    HAS_IFC = True
except:
    HAS_IFC = False
    ifcopenshell = None

HK_RULE = "HK Code of Practice for Fire Safety in Buildings 2011 (2024 Ed.) Table B2"

def check_door_width(model, min_width_mm: float = 750.0):
    """
    Returns list of dict: {guid, name, tag, measured_mm, required_mm, delta_mm, status, rule}
    measured in mm (IFC length unit is meters by default, but OverallWidth may be in meters)
    We handle both: if value < 10, assume meters → *1000
    """
    results = []
    if model is None:
        return results
    # handle fallback dict model
    if isinstance(model, dict) and model.get("_fallback"):
        doors = [e for e in model.get("elements", []) if e.is_a()=="IfcDoor"]
    else:
        try:
            doors = model.by_type("IfcDoor")
        except:
            doors = []
    for d in doors:
        guid = getattr(d, "GlobalId", "")
        name = getattr(d, "Name", "") or getattr(d, "Tag", "") or "Unnamed Door"
        tag = getattr(d, "Tag", "") or ""
        # Try OverallWidth attribute
        width = getattr(d, "OverallWidth", None)
        # Try QTO / Psets
        if width is None and HAS_IFC:
            try:
                psets = ifcopenshell.util.element.get_psets(d)
                # Qto_DoorBaseQuantities
                qto = psets.get("Qto_DoorBaseQuantities", {})
                width = qto.get("OverallWidth") or qto.get("Width")
                if width is None:
                    # search any pset with Width
                    for ps in psets.values():
                        if isinstance(ps, dict) and "Width" in ps:
                            width = ps["Width"]
                            break
            except:
                pass
        # fallback: OverallHeight misuse? no
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
                "reason": "No OverallWidth / Qto found"
            })
            continue
        # normalize to mm
        try:
            w = float(width)
            # Heuristic: IFC SI is meters, so <5 means meters
            if w < 5:  # meters
                w_mm = w * 1000.0
            else:  # already mm
                w_mm = w
        except:
            w_mm = None

        if w_mm is None:
            status = "unknown"
            delta = None
        else:
            delta = round(w_mm - min_width_mm, 1)
            if w_mm >= min_width_mm:
                status = "pass"
            else:
                status = "fail"
        results.append({
            "guid": guid,
            "name": name,
            "tag": tag,
            "measured_mm": round(w_mm,1) if w_mm else None,
            "required_mm": min_width_mm,
            "delta_mm": delta,
            "status": status,
            "rule": HK_RULE,
            "type": "IfcDoor"
        })
    return results

def summarize_door_results(results):
    total = len(results)
    passed = sum(1 for r in results if r["status"]=="pass")
    failed = sum(1 for r in results if r["status"]=="fail")
    unknown = total - passed - failed
    return {"total": total, "passed": passed, "failed": failed, "unknown": unknown}
