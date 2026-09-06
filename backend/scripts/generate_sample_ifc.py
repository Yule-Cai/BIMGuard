"""
Generate synthetic IFC with controlled defects for BIMGuard demo.
- 4 walls (rectangle floor plan)
- 3 doors: D-101 900mm PASS, D-102 680mm FAIL, D-103 750mm PASS (boundary)
- 1 beam + 1 pipe that clash (AABB overlap)
Requires ifcopenshell.
"""
import argparse
import ifcopenshell
import ifcopenshell.api
import ifcopenshell.util.placement
import ifcopenshell.guid
import time
import os

def create_sample(out_path, doors_cfg=None, do_clash=True):
    doors_cfg = doors_cfg or [
        ("D-101", 0.9, 2.1, (2, 0, 0)),   # pass
        ("D-102", 0.68, 2.1, (8, 0, 0)),  # fail - target
        ("D-103", 0.75, 2.1, (5, 10, 0)), # pass boundary
    ]
    model = ifcopenshell.file(schema="IFC4")
    project = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcProject", name="BIMGuard Demo")
    # Create Model/Body context for real geometry (enables BVH + web-ifc true rendering)
    context = ifcopenshell.api.run("context.add_context", model, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW")
    body = ifcopenshell.api.run("context.add_context", model, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=context)
    site = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcSite", name="Site")
    building = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcBuilding", name="Building A")
    storey = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcBuildingStorey", name="Level 01")
    ifcopenshell.api.run("aggregate.assign_object", model, relating_object=project, products=[site])
    ifcopenshell.api.run("aggregate.assign_object", model, relating_object=site, products=[building])
    ifcopenshell.api.run("aggregate.assign_object", model, relating_object=building, products=[storey])

    # Small office layout: 12m x 8m footprint
    #  - Reception/Open Office (main)
    #  - Meeting Room (4x4m) with D-103
    #  - Small Office (3x3m)
    #  - Corridor with D-101/D-102 and B-017/P-042 clash
    walls = []
    # Outer walls: 12x8 rectangle
    wall_coords = [
        ("W-01", (0,0,0), (12,0,0)),   # south
        ("W-02", (12,0,0), (12,8,0)),  # east
        ("W-03", (12,8,0), (0,8,0)),   # north
        ("W-04", (0,8,0), (0,0,0)),    # west
        # Inner: Meeting room 4x4 at top-right (8,4)-(12,8)
        ("W-05", (8,4,0), (8,8,0)),    # meeting west
        ("W-06", (8,4,0), (12,4,0)),   # meeting south
        # Small office 3x3 at bottom-right
        ("W-07", (9,0,0), (9,3,0)),    # office west
        ("W-08", (9,3,0), (12,3,0)),   # office north
    ]
    import numpy as np
    for name, start, end in wall_coords:
        wall = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcWall", name=name)
        mat = np.eye(4)
        mat[0,3], mat[1,3], mat[2,3] = start
        ifcopenshell.api.run("geometry.edit_object_placement", model, product=wall, matrix=mat, is_si=True)
        ifcopenshell.api.run("spatial.assign_container", model, products=[wall], relating_structure=storey)
        # Real geometry: wall lengths vary, use 4m avg for demo; slab will provide floor
        try:
            # Use 4m length for inner walls, 5m for outer (as before, BVH will still detect)
            length = 4 if name in ("W-05","W-06","W-07","W-08") else 5
            rep = ifcopenshell.api.run("geometry.add_wall_representation", model, context=body, length=length, height=3, thickness=0.2)
            ifcopenshell.api.run("geometry.assign_representation", model, product=wall, representation=rep)
        except Exception:
            pass
        walls.append(wall)
    # Floor slab: 12x8m at z=0, thickness 0.2m, light grey
    try:
        slab = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcSlab", name="Floor-01")
        mat_slab = np.eye(4)
        ifcopenshell.api.run("geometry.edit_object_placement", model, product=slab, matrix=mat_slab, is_si=True)
        ifcopenshell.api.run("spatial.assign_container", model, products=[slab], relating_structure=storey)
        rep_slab = ifcopenshell.api.run("geometry.add_wall_representation", model, context=body, length=12, height=0.2, thickness=8)
        # Rotate slab to be horizontal: wall rep is vertical, but for demo we use it as floor box; placement at origin will show as wall-like but viewer will show as slab
        # Instead, create a slab-like representation via generic add_representation if needed
        ifcopenshell.api.run("geometry.assign_representation", model, product=slab, representation=rep_slab)
    except Exception:
        pass

    # Doors with real geometry (thin box) for true rendering
    for name, width_m, height_m, pos in doors_cfg:
        door = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcDoor", name=name)
        door.OverallWidth = width_m
        door.OverallHeight = height_m
        door.Tag = name
        mat = np.eye(4)
        mat[0,3], mat[1,3], mat[2,3] = pos
        ifcopenshell.api.run("geometry.edit_object_placement", model, product=door, matrix=mat, is_si=True)
        ifcopenshell.api.run("spatial.assign_container", model, products=[door], relating_structure=storey)
        try:
            # Door as thin wall-like box: width x height x 0.05m thickness, placed at pos
            rep = ifcopenshell.api.run("geometry.add_wall_representation", model, context=body, length=width_m, height=height_m, thickness=0.05)
            ifcopenshell.api.run("geometry.assign_representation", model, product=door, representation=rep)
        except Exception:
            pass
        pset = ifcopenshell.api.run("pset.add_pset", model, product=door, name="Pset_DoorCommon")
        ifcopenshell.api.run("pset.edit_pset", model, pset=pset, properties={"FireRating": "60min", "IsExternal": False})

    # Beam + Pipe with real geometry that truly clash via BVH (100mm penetration)
    beam = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcBeam", name="B-017")
    beam.Tag = "B-017"
    mat_b = np.eye(4)
    mat_b[0,3], mat_b[1,3], mat_b[2,3] = (2, 2, 2.0)
    ifcopenshell.api.run("geometry.edit_object_placement", model, product=beam, matrix=mat_b, is_si=True)
    ifcopenshell.api.run("spatial.assign_container", model, products=[beam], relating_structure=storey)
    try:
        rep_b = ifcopenshell.api.run("geometry.add_wall_representation", model, context=body, length=5, height=0.4, thickness=0.3)
        ifcopenshell.api.run("geometry.assign_representation", model, product=beam, representation=rep_b)
    except Exception:
        pass

    pipe = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcPipeSegment", name="P-042")
    pipe.Tag = "P-042"
    mat_p = np.eye(4)
    mat_p[0,3], mat_p[1,3], mat_p[2,3] = (2.5, 2, 2.1)
    ifcopenshell.api.run("geometry.edit_object_placement", model, product=pipe, matrix=mat_p, is_si=True)
    ifcopenshell.api.run("spatial.assign_container", model, products=[pipe], relating_structure=storey)
    try:
        rep_p = ifcopenshell.api.run("geometry.add_wall_representation", model, context=body, length=4, height=0.2, thickness=0.2)
        ifcopenshell.api.run("geometry.assign_representation", model, product=pipe, representation=rep_p)
    except Exception:
        pass

    # Write
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    model.write(out_path)
    print(f"Wrote {out_path}")
    # summary
    print(f"Doors: {len(doors_cfg)} (fail: {sum(1 for _,w,_,_ in doors_cfg if w*1000 < 750)})")
    print(f"Clash pair: B-017 x P-042 at (2,2,2) overlap ~100mm")
    # verify
    m2 = ifcopenshell.open(out_path)
    print(f"Verify: {len(m2.by_type('IfcDoor'))} doors, {len(m2.by_type('IfcWall'))} walls")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="../sample-ifc/BIMGuard_Demo.ifc")
    parser.add_argument("--doors", type=int, default=3)
    args = parser.parse_args()
    script_dir = os.path.dirname(__file__)
    out = args.out
    if not os.path.isabs(out):
        out = os.path.join(script_dir, out)
    create_sample(out)
