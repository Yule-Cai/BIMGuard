"""Quick API test without running server — calls engine directly."""
from app import ifc_engine
from app.rules.door_width import check_door_width
from app.rules.clash import detect_clashes
from app.agent.tools import route_message

def test():
    import os
    base = os.path.dirname(os.path.dirname(__file__))
    path = os.path.join(base, "sample-ifc/BIMGuard_Demo.ifc")
    alt = os.path.join(os.path.dirname(__file__), "../sample-ifc/BIMGuard_Demo.ifc")
    if not os.path.exists(path):
        path = alt
    if not os.path.exists(path):
        path = "sample-ifc/BIMGuard_Demo.ifc"
    ifc_engine.set_current_file(path)
    model = ifc_engine.get_current_model()
    assert model is not None, "model not loaded"
    doors = check_door_width(model, 750)
    assert len(doors)==3, f"expected 3 doors, got {len(doors)}"
    fails = [d for d in doors if d["status"]=="fail"]
    assert len(fails)==1 and fails[0]["name"]=="D-102", f"expected D-102 fail, got {fails}"
    assert fails[0]["measured_mm"]==680.0
    clashes = detect_clashes(model)
    assert len(clashes)>=1, "expected clash"
    assert clashes[0]["severity"]=="high"
    print("✓ door + clash checks pass")
    # agent
    r = route_message("Why is D-102 a problem?", 750)
    assert "680" in r["reply"] and "750" in r["reply"], "agent reply missing evidence"
    print("✓ agent mock pass")
    print("All tests passed — ready for video/demo")
    print(f"Doors: {doors}")
    print(f"Clashes: {clashes}")

if __name__=="__main__":
    test()
