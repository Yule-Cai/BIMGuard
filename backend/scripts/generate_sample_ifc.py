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
    # Project setup via API
    # Root
    project = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcProject", name="BIMGuard Demo")
    # Units - keep default meters
    # Contexts / site / building / storey
    site = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcSite", name="Site")
    building = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcBuilding", name="Building A")
    storey = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcBuildingStorey", name="Level 01")
    # Aggregate
    ifcopenshell.api.run("aggregate.assign_object", model, relating_object=project, products=[site])
    ifcopenshell.api.run("aggregate.assign_object", model, relating_object=site, products=[building])
    ifcopenshell.api.run("aggregate.assign_object", model, relating_object=building, products=[storey])

    # Owner history minimal
    # Create walls - simple placements
    walls = []
    wall_coords = [
        ("W-01", (0,0,0), (10,0,0)),
        ("W-02", (10,0,0), (10,10,0)),
        ("W-03", (10,10,0), (0,10,0)),
        ("W-04", (0,10,0), (0,0,0)),
    ]
    import numpy as np
    for name, start, end in wall_coords:
        wall = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcWall", name=name)
        mat = np.eye(4)
        mat[0,3], mat[1,3], mat[2,3] = start
        ifcopenshell.api.run("geometry.edit_object_placement", model, product=wall, matrix=mat, is_si=True)
        ifcopenshell.api.run("spatial.assign_container", model, products=[wall], relating_structure=storey)
        walls.append(wall)

    # Doors
    for name, width_m, height_m, pos in doors_cfg:
        door = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcDoor", name=name)
        door.OverallWidth = width_m
        door.OverallHeight = height_m
        door.Tag = name
        mat = np.eye(4)
        mat[0,3], mat[1,3], mat[2,3] = pos
        ifcopenshell.api.run("geometry.edit_object_placement", model, product=door, matrix=mat, is_si=True)
        ifcopenshell.api.run("spatial.assign_container", model, products=[door], relating_structure=storey)
        # Add Pset for redundancy
        pset = ifcopenshell.api.run("pset.add_pset", model, product=door, name="Pset_DoorCommon")
        ifcopenshell.api.run("pset.edit_pset", model, pset=pset, properties={"FireRating": "60min", "IsExternal": False})

    # Beam + Pipe that clash (same position) — intentionally without shape for demo fallback
    beam = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcBeam", name="B-017")
    beam.Tag = "B-017"
    mat_b = np.eye(4)
    mat_b[0,3], mat_b[1,3], mat_b[2,3] = (2, 2, 2.0)
    ifcopenshell.api.run("geometry.edit_object_placement", model, product=beam, matrix=mat_b, is_si=True)
    ifcopenshell.api.run("spatial.assign_container", model, products=[beam], relating_structure=storey)

    pipe = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcPipeSegment", name="P-042")
    pipe.Tag = "P-042"
    mat_p = np.eye(4)
    mat_p[0,3], mat_p[1,3], mat_p[2,3] = (2.5, 2, 2.1)
    ifcopenshell.api.run("geometry.edit_object_placement", model, product=pipe, matrix=mat_p, is_si=True)
    ifcopenshell.api.run("spatial.assign_container", model, products=[pipe], relating_structure=storey)

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
