import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), ".."))

from backend.app import ifc_engine
from backend.app.rules.door_width import check_door_width
from backend.app.rules.clash import detect_clashes

SAMPLE = os.path.join(os.path.dirname(__file__), "../../sample-ifc/BIMGuard_Demo.ifc")

def setup_module():
    ifc_engine.set_current_file(os.path.abspath(SAMPLE))

def test_door_width():
    model = ifc_engine.get_current_model()
    res = check_door_width(model, 750)
    assert len(res) == 3
    fails = [r for r in res if r["status"]=="fail"]
    assert len(fails)==1
    assert fails[0]["name"]=="D-102"
    assert fails[0]["measured_mm"]==680.0
    assert fails[0]["delta_mm"]==-70.0

def test_door_850():
    model = ifc_engine.get_current_model()
    res = check_door_width(model, 850)
    # D-102 680 fail, D-103 750 fail, D-101 900 pass → 1 pass 2 fail
    fails = [r for r in res if r["status"]=="fail"]
    assert len(fails)==2

def test_clash():
    model = ifc_engine.get_current_model()
    cl = detect_clashes(model)
    assert len(cl)>=1
    assert cl[0]["a_name"]=="B-017" or cl[0]["b_name"]=="B-017"
    assert cl[0]["severity"]=="high"
    assert cl[0]["penetration_mm"]>=50

def test_elements():
    els = ifc_engine.list_elements(limit=20)
    assert len(els)>=9
    types = {e.is_a() for e in els}
    assert "IfcDoor" in types and "IfcWall" in types
