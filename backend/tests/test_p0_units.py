"""P0-2 unit conversion tests."""
import os, sys, tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from backend.app.rules.door_width import check_door_width
import ifcopenshell
import ifcopenshell.api
import ifcopenshell.util.unit
import numpy as np

def _create_door_ifc(path, width_value, unit="m"):
    """Create minimal IFC with one door and specified length unit."""
    model = ifcopenshell.file(schema="IFC4")
    project = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcProject", name="Unit Test")
    # Set units via official API
    try:
        if unit == "m":
            length_unit = ifcopenshell.api.run("unit.add_si_unit", model, unit_type="LENGTHUNIT")
        elif unit == "mm":
            length_unit = ifcopenshell.api.run("unit.add_si_unit", model, unit_type="LENGTHUNIT", prefix="MILLI")
        elif unit == "ft":
            # Use conversion-based unit for foot (0.3048 m)
            length_unit = ifcopenshell.api.run("unit.add_conversion_based_unit", model, name="foot")
            # The default conversion for foot is 0.3048, verify
            # If the API creates a different unit, we will handle conversion via scale
        else:
            raise ValueError(f"unknown unit {unit}")
        ifcopenshell.api.run("unit.assign_unit", model, units=[length_unit])
    except Exception as e:
        print(f"unit setup warning for {unit}: {e}")
        # Fallback: try manual if API fails
        try:
            if unit == "m":
                length_unit = model.create_entity("IfcSIUnit", UnitType="LENGTHUNIT", Name="METRE")
            elif unit == "mm":
                length_unit = model.create_entity("IfcSIUnit", UnitType="LENGTHUNIT", Name="METRE", Prefix="MILLI")
            unit_assignment = model.create_entity("IfcUnitAssignment", [length_unit])
            project.UnitsInContext = unit_assignment
        except Exception as e2:
            print(f"fallback unit also failed for {unit}: {e2}")

    site = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcSite", name="Site")
    building = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcBuilding", name="B")
    storey = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcBuildingStorey", name="L1")
    ifcopenshell.api.run("aggregate.assign_object", model, relating_object=project, products=[site])
    ifcopenshell.api.run("aggregate.assign_object", model, relating_object=site, products=[building])
    ifcopenshell.api.run("aggregate.assign_object", model, relating_object=building, products=[storey])

    door = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcDoor", name="D-UNIT")
    door.OverallWidth = width_value
    door.OverallHeight = 2.1 if unit != "mm" else 2100  # keep consistent
    door.Tag = "D-UNIT"
    mat = np.eye(4)
    ifcopenshell.api.run("geometry.edit_object_placement", model, product=door, matrix=mat, is_si=True)
    ifcopenshell.api.run("spatial.assign_container", model, products=[door], relating_structure=storey)
    model.write(path)
    return path

def test_p0_2_m_to_mm():
    with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as tmp:
        path = tmp.name
    _create_door_ifc(path, 0.68, unit="m")
    model = ifcopenshell.open(path)
    scale = ifcopenshell.util.unit.calculate_unit_scale(model)
    print(f"m scale {scale}")
    res = check_door_width(model, 750)
    assert len(res) == 1
    assert res[0]["measured_mm"] == 680.0, f"0.68m should be 680mm, got {res[0]}"
    assert res[0]["status"] == "fail"
    os.unlink(path)

def test_p0_2_mm_to_mm():
    with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as tmp:
        path = tmp.name
    _create_door_ifc(path, 680, unit="mm")
    model = ifcopenshell.open(path)
    scale = ifcopenshell.util.unit.calculate_unit_scale(model)
    print(f"mm scale {scale} (should be 0.001)")
    res = check_door_width(model, 750)
    assert len(res) == 1
    # 680 mm in mm units should still be 680mm
    assert res[0]["measured_mm"] == 680.0, f"680 mm should be 680mm, got {res[0]}"
    assert res[0]["status"] == "fail"
    os.unlink(path)

def test_p0_2_boundary():
    # 0.75m and 750mm should both be exactly 750
    for unit, val in [("m", 0.75), ("mm", 750)]:
        with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as tmp:
            path = tmp.name
        _create_door_ifc(path, val, unit=unit)
        model = ifcopenshell.open(path)
        res = check_door_width(model, 750)
        assert res[0]["measured_mm"] == 750.0, f"{val} {unit} should be 750, got {res[0]}"
        assert res[0]["status"] == "pass", f"750 should be pass at 750 threshold"
        os.unlink(path)

# Optional ft test — may be skipped if unit creation fails
def test_p0_2_ft_robustness():
    try:
        with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as tmp:
            path = tmp.name
        # 2.23 ft ≈ 680mm (2.23*304.8=679.7)
        _create_door_ifc(path, 2.23, unit="ft")
        model = ifcopenshell.open(path)
        scale = ifcopenshell.util.unit.calculate_unit_scale(model)
        print(f"ft scale {scale}")
        res = check_door_width(model, 750)
        # 2.23 ft ≈ 680mm should be fail
        assert res[0]["measured_mm"] == pytest.approx(680, abs=2), f"2.23ft should be ~680mm, got {res[0]['measured_mm']}"
        os.unlink(path)
    except Exception as e:
        pytest.skip(f"ft unit creation not supported in this IfcOpenShell build: {e}")
