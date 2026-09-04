import itertools
import logging
import os

logger = logging.getLogger("bimguard.clash")

try:
    import ifcopenshell
    import ifcopenshell.util.placement
    HAS_IFC = True
except Exception:
    HAS_IFC = False
    ifcopenshell = None

try:
    import ifcopenshell.geom
    HAS_GEOM = True
except Exception:
    HAS_GEOM = False


def _severity(penetration_mm: float) -> str:
    if penetration_mm > 50:
        return "high"
    if penetration_mm > 10:
        return "medium"
    return "low"


def _element_name(el):
    name = getattr(el, "Name", None) or getattr(el, "Tag", None)
    if name:
        return str(name)
    try:
        return str(el.get_argument(2) or el.is_a())
    except Exception:
        return str(el.is_a())


def _element_guid(el):
    guid = getattr(el, "GlobalId", None)
    if guid:
        return str(guid)
    try:
        return str(el.get_argument(0) or "")
    except Exception:
        return ""


def _collect_elements(model, types):
    elements = []
    for ifc_type in types:
        try:
            elements.extend(model.by_type(ifc_type))
        except Exception:
            pass

    # by_type on IFC inheritance can make generic classes overlap with specific
    # classes; deduplicate on GlobalId / entity id before clashing.
    unique = []
    seen = set()
    for el in elements:
        key = _element_guid(el)
        if not key:
            try:
                key = f"#{el.id()}"
            except Exception:
                key = repr(el)
        if key not in seen:
            seen.add(key)
            unique.append(el)
    return unique


def _detect_bvh(model, elems_a, elems_b, tolerance):
    """Run exact IFC geometry intersection checks with an IfcOpenShell BVH tree.

    Follows IfcOpenShell's documented geometry-tree workflow: build the tree with
    the geometry iterator, then clash the two IFC element sets. Distances returned
    by clash_intersection_many() are metres and are converted to millimetres here.

    Returns (results, geometry_count). An empty result with geometry_count > 0 is
    a valid 'no clashes' result and must not fall back to guessed dimensions.
    """
    if not (HAS_GEOM and HAS_IFC):
        return [], 0

    tree = ifcopenshell.geom.tree()
    if not hasattr(tree, "clash_intersection_many"):
        logger.warning("IfcOpenShell build has no clash_intersection_many")
        return [], 0

    settings = ifcopenshell.geom.settings()
    workers = max(1, min(4, os.cpu_count() or 1))
    iterator = ifcopenshell.geom.iterator(settings, model, workers)

    geometry_count = 0
    if iterator.initialize():
        while True:
            tree.add_element(iterator.get())  # triangulation -> BVH tree
            geometry_count += 1
            if not iterator.next():
                break

    if geometry_count == 0:
        return [], 0

    clashes = tree.clash_intersection_many(
        elems_a,
        elems_b,
        tolerance=float(tolerance),
        check_all=True,
    )

    results = []
    clash_type_names = ["protrusion", "pierce", "collision", "clearance"]
    for clash in clashes:
        a = clash.a
        b = clash.b
        distance_m = max(0.0, float(clash.distance))
        penetration_mm = round(distance_m * 1000.0, 1)
        try:
            clash_type = clash_type_names[int(clash.clash_type)]
        except Exception:
            clash_type = "intersection"

        try:
            p1 = [round(float(v), 5) for v in clash.p1]
            p2 = [round(float(v), 5) for v in clash.p2]
        except Exception:
            p1 = None
            p2 = None

        results.append({
            "a_guid": _element_guid(a),
            "a_name": _element_name(a),
            "a_type": a.is_a(),
            "b_guid": _element_guid(b),
            "b_name": _element_name(b),
            "b_type": b.is_a(),
            "penetration_mm": penetration_mm,
            "severity": _severity(penetration_mm),
            "clash_type": clash_type,
            "method": "ifcopenshell_bvh",
            "p1": p1,
            "p2": p2,
        })

    return results, geometry_count


# ---------------------------------------------------------------------------
# Synthetic-demo fallback
# ---------------------------------------------------------------------------
# BIMGuard_Demo.ifc intentionally contains semantic IFC entities and placements
# but no shape representations, so it cannot populate a geometry tree. These
# rough AABBs exist only to keep that controlled no-geometry demo usable. They
# are never used when a real IFC successfully contributes geometry to the BVH.


def _get_synthetic_aabb(el):
    try:
        if hasattr(el, "_mock_placement_dict") and el._mock_placement_dict:
            x = el._mock_placement_dict["x"]
            y = el._mock_placement_dict["y"]
            z = el._mock_placement_dict["z"]
        elif isinstance(getattr(el, "ObjectPlacement", None), dict):
            x = el.ObjectPlacement["x"]
            y = el.ObjectPlacement["y"]
            z = el.ObjectPlacement["z"]
        elif HAS_IFC and hasattr(el, "ObjectPlacement") and el.ObjectPlacement:
            m = ifcopenshell.util.placement.get_local_placement(el.ObjectPlacement)
            if m is None:
                return None
            x, y, z = float(m[0, 3]), float(m[1, 3]), float(m[2, 3])
        else:
            return None

        t = el.is_a()
        if t == "IfcWall":
            return (x, x + 5, y - 0.1, y + 0.1, z, z + 3)
        if t == "IfcBeam":
            return (x, x + 5, y - 0.15, y + 0.15, z + 2, z + 2.4)
        if t == "IfcColumn":
            return (x - 0.2, x + 0.2, y - 0.2, y + 0.2, z, z + 3)
        if t in (
            "IfcPipeSegment",
            "IfcFlowSegment",
            "IfcDuctSegment",
            "IfcDistributionElement",
            "IfcDistributionFlowElement",
        ):
            return (x, x + 4, y - 0.05, y + 0.05, z + 2.1, z + 2.2)
        if t == "IfcSlab":
            return (x, x + 6, y, y + 6, z + 3, z + 3.2)
        return (x - 0.5, x + 0.5, y - 0.5, y + 0.5, z, z + 1)
    except Exception:
        return None


def _aabb_intersect(a, b):
    return not (
        a[1] < b[0]
        or b[1] < a[0]
        or a[3] < b[2]
        or b[3] < a[2]
        or a[5] < b[4]
        or b[5] < a[4]
    )


def _aabb_penetration_mm(a, b):
    ox = min(a[1], b[1]) - max(a[0], b[0])
    oy = min(a[3], b[3]) - max(a[2], b[2])
    oz = min(a[5], b[5]) - max(a[4], b[4])
    if ox < 0 or oy < 0 or oz < 0:
        return 0.0
    return round(min(ox, oy, oz) * 1000.0, 1)


def _detect_synthetic_aabb(elems_a, elems_b):
    results = []
    for a, b in itertools.product(elems_a, elems_b):
        if _element_guid(a) == _element_guid(b):
            continue
        ab = _get_synthetic_aabb(a)
        bb = _get_synthetic_aabb(b)
        if ab is None or bb is None or not _aabb_intersect(ab, bb):
            continue
        penetration_mm = _aabb_penetration_mm(ab, bb)
        results.append({
            "a_guid": _element_guid(a),
            "a_name": _element_name(a),
            "a_type": a.is_a(),
            "b_guid": _element_guid(b),
            "b_name": _element_name(b),
            "b_type": b.is_a(),
            "penetration_mm": penetration_mm,
            "severity": _severity(penetration_mm),
            "clash_type": "synthetic_overlap",
            "method": "synthetic_aabb_fallback",
            "p1": None,
            "p2": None,
        })
    return results


def _deduplicate(clashes):
    seen = set()
    unique = []
    for clash in clashes:
        key = tuple(sorted([clash["a_guid"], clash["b_guid"]]))
        if key not in seen:
            seen.add(key)
            unique.append(clash)
    return unique[:50]


def detect_clashes(model, types_a=None, types_b=None, tolerance=0.001):
    """Detect structural-vs-MEP intersections.

    Real IFCs with geometric representations are checked using IfcOpenShell's BVH
    geometry tree and clash_intersection_many(). The rough AABB path is restricted
    to the repository's controlled synthetic/no-geometry demo and is explicitly
    labelled in every result.

    ``tolerance`` is in metres, matching IfcOpenShell's geometry-tree API.
    """
    if model is None:
        return []

    if types_a is None:
        types_a = ["IfcWall", "IfcBeam", "IfcColumn", "IfcSlab"]
    if types_b is None:
        types_b = [
            "IfcPipeSegment",
            "IfcFlowSegment",
            "IfcDuctSegment",
            "IfcDistributionElement",
            "IfcPipeFitting",
        ]

    is_fallback = isinstance(model, dict) and model.get("_fallback")
    if is_fallback:
        all_elements = model.get("elements", [])
        elems_a = [e for e in all_elements if e.is_a() in types_a]
        elems_b = [e for e in all_elements if e.is_a() in types_b]
        if not elems_b:
            elems_b = [
                e
                for e in all_elements
                if e.is_a() in ("IfcDistributionFlowElement", "IfcPipeSegment")
            ]
        return _deduplicate(_detect_synthetic_aabb(elems_a, elems_b))

    elems_a = _collect_elements(model, types_a)
    elems_b = _collect_elements(model, types_b)
    if not elems_b:
        try:
            elems_b = _collect_elements(model, ["IfcDistributionFlowElement"])
        except Exception:
            elems_b = []
    if not elems_a or not elems_b:
        return []

    if HAS_GEOM:
        try:
            bvh_results, geometry_count = _detect_bvh(
                model, elems_a, elems_b, tolerance
            )
            if geometry_count > 0:
                # Even an empty list is authoritative: geometry existed and no
                # qualifying intersection was found. Never invent AABB clashes.
                return _deduplicate(bvh_results)
        except Exception as exc:
            logger.warning("BVH clash detection failed: %s", exc)

    # A real IFC that cannot be geometrically evaluated should fail conservative:
    # return no fabricated clashes. The API/UI can still perform semantic checks.
    logger.warning(
        "No usable IFC geometry for clash detection; synthetic AABB fallback skipped"
    )
    return []
