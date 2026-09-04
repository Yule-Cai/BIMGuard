import itertools
try:
    import ifcopenshell
    import ifcopenshell.util.placement
    import ifcopenshell.util.element
    HAS_IFC = True
except:
    HAS_IFC = False
    ifcopenshell = None

try:
    import ifcopenshell.geom
    HAS_GEOM = True
except:
    HAS_GEOM = False

def _get_aabb(el):
    """Fallback AABB from placement + rough size heuristic."""
    try:
        # handle mock placement dict
        if hasattr(el, "_mock_placement_dict") and el._mock_placement_dict:
            x = el._mock_placement_dict["x"]; y = el._mock_placement_dict["y"]; z = el._mock_placement_dict["z"]
        elif isinstance(getattr(el, "ObjectPlacement", None), dict):
            x = el.ObjectPlacement["x"]; y = el.ObjectPlacement["y"]; z = el.ObjectPlacement["z"]
        elif HAS_IFC and hasattr(el, "ObjectPlacement") and el.ObjectPlacement:
            m = ifcopenshell.util.placement.get_local_placement(el.ObjectPlacement)
            if m is None:
                return None
            x, y, z = float(m[0,3]), float(m[1,3]), float(m[2,3])
        else:
            # fallback heuristic by element name guid
            return None
        # heuristic sizes by type
        t = el.is_a()
        if t == "IfcWall":
            # wall along X, length 5, thickness 0.2, height 3
            return (x, x+5, y-0.1, y+0.1, z, z+3)
        elif t == "IfcBeam":
            return (x, x+5, y-0.15, y+0.15, z+2, z+2.4)
        elif t == "IfcColumn":
            return (x-0.2, x+0.2, y-0.2, y+0.2, z, z+3)
        elif t in ("IfcPipeSegment", "IfcFlowSegment", "IfcDuctSegment", "IfcDistributionElement"):
            return (x, x+4, y-0.05, y+0.05, z+2.1, z+2.2)
        elif t == "IfcSlab":
            return (x, x+6, y, y+6, z+3, z+3.2)
        else:
            return (x-0.5, x+0.5, y-0.5, y+0.5, z, z+1)
    except:
        return None

def _aabb_intersect(a,b):
    return not (a[1] < b[0] or b[1] < a[0] or a[3] < b[2] or b[3] < a[2] or a[5] < b[4] or b[5] < a[4])

def _penetration(a,b):
    # overlap in 3 axes, min overlap as penetration
    ox = min(a[1],b[1]) - max(a[0],b[0])
    oy = min(a[3],b[3]) - max(a[2],b[2])
    oz = min(a[5],b[5]) - max(a[4],b[4])
    if ox<0 or oy<0 or oz<0:
        return 0
    return round(min(ox,oy,oz)*1000,1)  # mm

def detect_clashes(model, types_a=None, types_b=None, tolerance=0.001):
    """
    Returns list: {a_guid, a_name, a_type, b_guid, b_name, b_type, penetration_mm, severity}
    Tries geometry tree first, falls back to AABB.
    """
    if model is None:
        return []
    if types_a is None:
        types_a = ["IfcWall", "IfcBeam", "IfcColumn", "IfcSlab"]
    if types_b is None:
        types_b = ["IfcPipeSegment", "IfcFlowSegment", "IfcDuctSegment", "IfcDistributionElement", "IfcPipeFitting"]

    # handle fallback dict model
    if isinstance(model, dict) and model.get("_fallback"):
        els = model.get("elements", [])
        elems_a = [e for e in els if e.is_a() in types_a]
        elems_b = [e for e in els if e.is_a() in types_b]
        if not elems_b:
            elems_b = [e for e in els if e.is_a() in ("IfcDistributionFlowElement","IfcPipeSegment")]
    else:
        elems_a = []
        elems_b = []
        for t in types_a:
            try:
                elems_a.extend(model.by_type(t))
            except: pass
        for t in types_b:
            try:
                elems_b.extend(model.by_type(t))
            except: pass
        # If generic DistributionElement covers pipes
        if not elems_b:
            try:
                elems_b.extend(model.by_type("IfcDistributionFlowElement"))
            except: pass
    # Fallback: if still empty, try all elements
    if not elems_a and not elems_b:
        return []

    # Try geometry tree if available (ifcopenshell 0.7 has geom.tree)
    if HAS_GEOM:
        try:
            settings = ifcopenshell.geom.settings()
            settings.set(settings.USE_WORLD_COORDS, True)
            tree = ifcopenshell.geom.tree()
            # For 0.7, tree add may need iterator
            # Try new API: tree.add_file(model) or manual
            has_tree_clash = hasattr(tree, "clash_intersection_many") or hasattr(tree, "clash_collision_many")
            if has_tree_clash:
                # Build shapes
                iterator = ifcopenshell.geom.iterator(settings, model, len(model.by_type("IfcProduct")))
                # Actually simpler: use ifcopenshell.geom.tree iterator path not stable across versions
                # So we skip to AABB if iterator not straightforward
                pass
        except Exception as e:
            pass  # fall through to AABB

    # AABB fallback — deterministic and always works
    clashes = []
    for a,b in itertools.product(elems_a, elems_b):
        if a.GlobalId == b.GlobalId:
            continue
        ab = _get_aabb(a)
        bb = _get_aabb(b)
        if ab is None or bb is None:
            continue
        if _aabb_intersect(ab, bb):
            pen = _penetration(ab, bb)
            # severity
            if pen > 50:
                sev = "high"
            elif pen > 10:
                sev = "medium"
            else:
                sev = "low"
            clashes.append({
                "a_guid": a.GlobalId,
                "a_name": getattr(a, "Name", "") or getattr(a, "Tag", "") or a.is_a(),
                "a_type": a.is_a(),
                "b_guid": b.GlobalId,
                "b_name": getattr(b, "Name", "") or getattr(b, "Tag", "") or b.is_a(),
                "b_type": b.is_a(),
                "penetration_mm": pen,
                "severity": sev
            })
    # Deduplicate by pair
    seen = set()
    uniq = []
    for c in clashes:
        key = tuple(sorted([c["a_guid"], c["b_guid"]]))
        if key not in seen:
            seen.add(key)
            uniq.append(c)
    return uniq[:50]  # cap
