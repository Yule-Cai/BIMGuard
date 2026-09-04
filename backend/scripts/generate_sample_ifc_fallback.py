"""Fallback IFC generator — no ifcopenshell required, writes STEP text."""
import os
import uuid

def gen_guid():
    # simple guid-like (not real IFC guid but ok for demo)
    return uuid.uuid4().hex[:22]

header = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('BIMGuard Demo IFC'),'2;1');
FILE_NAME('BIMGuard_Demo.ifc','2026-09-04T00:00:00',(''),(''),'','','');
FILE_SCHEMA(('IFC4'));
ENDSEC;
DATA;
#1=IFCPERSON($,$,'',$, $,$,$,$);
#2=IFCORGANIZATION($,'BIMGuard',$,$,$);
#3=IFCPERSONANDORGANIZATION(#1,#2,$);
#4=IFCAPPLICATION(#2,'BIMGuard','BIMGuard','BIMGuard');
#5=IFCOWNERHISTORY(#3,#4,$,.NOCHANGE.,$,#3,#4,0);
#10=IFCPROJECT('{proj_guid}',#5,'BIMGuard Demo',$,$,$,$,(#20),#30);
#20=IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.0E-05,#15,$);
#15=IFCAXIS2PLACEMENT3D(#6,$,$);
#6=IFCCARTESIANPOINT((0.,0.,0.));
#30=IFCUNITASSIGNMENT((#31,#32));
#31=IFCSIUNIT(*,.LENGTHUNIT.,$,.METRE.);
#32=IFCSIUNIT(*,.AREAUNIT.,$,.SQUARE_METRE.);
#50=IFCSITE('{site_guid}',#5,'Site',$,$,#60,$,$,.ELEMENT.,$,$,$,$,$);
#60=IFCLOCALPLACEMENT($,#15);
#51=IFCBUILDING('{bld_guid}',#5,'Building A',$,$,#61,$,$,.ELEMENT.,$,$,$);
#61=IFCLOCALPLACEMENT(#60,#15);
#52=IFCBUILDINGSTOREY('{storey_guid}',#5,'Level 01',$,$,#62,$,$,.ELEMENT.,0.);
#62=IFCLOCALPLACEMENT(#61,#15);
#53=IFCRELAGGREGATES('ag1',#5,$,$,#10,(#50));
#54=IFCRELAGGREGATES('ag2',#5,$,$,#50,(#51));
#55=IFCRELAGGREGATES('ag3',#5,$,$,#51,(#52));
"""

footer = """
ENDSEC;
END-ISO-10303-21;
"""

def make_door(guid, name, width, height, x, y, z, id_start):
    # // PLACEMENT comment for fallback parser
    return f"// PLACEMENT {name} {x} {y} {z}\n#{id_start}=IFCDOOR('{guid}',#5,'{name}','{name}',$,$,{width},{height},$,$,$,$);\n#{id_start+1}=IFCRELCONTAINEDINSPATIALSTRUCTURE('rel{id_start}',#5,$,$,(#{id_start}),#52);\n"

def make_wall(guid, name, id_start):
    return f"#{id_start}=IFCWALL('{guid}',#5,'{name}',$,$,#62,$,$,.ELEMENT.);\n#{id_start+1}=IFCRELCONTAINEDINSPATIALSTRUCTURE('rel{id_start}',#5,$,$,(#{id_start}),#52);\n"

def make_beam(guid, name, x,y,z, id_start):
    return f"// PLACEMENT {name} {x} {y} {z}\n#{id_start}=IFCBEAM('{guid}',#5,'{name}',$,$,#70,$,$,.ELEMENT.);\n#70=IFCLOCALPLACEMENT(#62,#71);\n#71=IFCAXIS2PLACEMENT3D(#72,$,$);\n#72=IFCCARTESIANPOINT(({x},{y},{z}));\n#{id_start+1}=IFCRELCONTAINEDINSPATIALSTRUCTURE('rel{id_start}',#5,$,$,(#{id_start}),#52);\n"

def make_pipe(guid, name, x,y,z, id_start):
    return f"// PLACEMENT {name} {x} {y} {z}\n#{id_start}=IFCPIPESEGMENT('{guid}',#5,'{name}',$,$,#80,$,$,.ELEMENT.);\n#80=IFCLOCALPLACEMENT(#62,#81);\n#81=IFCAXIS2PLACEMENT3D(#82,$,$);\n#82=IFCCARTESIANPOINT(({x},{y},{z}));\n#{id_start+1}=IFCRELCONTAINEDINSPATIALSTRUCTURE('rel{id_start}',#5,$,$,(#{id_start}),#52);\n"

def generate(out_path):
    proj_guid = gen_guid()
    site_guid = gen_guid()
    bld_guid = gen_guid()
    storey_guid = gen_guid()
    hdr = header.format(proj_guid=proj_guid, site_guid=site_guid, bld_guid=bld_guid, storey_guid=storey_guid)
    body = ""
    # walls
    wall_names = ["W-01","W-02","W-03","W-04"]
    cur = 100
    for wn in wall_names:
        body += make_wall(gen_guid(), wn, cur)
        cur += 10
    # doors: D-101 0.9 pass, D-102 0.68 fail, D-103 0.75 pass
    doors = [("D-101",0.9,2.1,2,0,0), ("D-102",0.68,2.1,8,0,0), ("D-103",0.75,2.1,5,10,0)]
    for name,w,h,x,y,z in doors:
        body += make_door(gen_guid(), name, w, h, x,y,z, cur)
        cur += 10
    # beam + pipe clash
    body += make_beam(gen_guid(), "B-017", 2,2,2.0, cur); cur+=10
    body += make_pipe(gen_guid(), "P-042", 2.5,2,2.1, cur); cur+=10

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(hdr)
        f.write(body)
        f.write(footer)
    print(f"Wrote fallback IFC to {out_path} ({len(body)} body bytes)")

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="../../sample-ifc/BIMGuard_Demo.ifc")
    args = p.parse_args()
    script_dir = os.path.dirname(__file__)
    out = args.out
    if not os.path.isabs(out):
        out = os.path.join(script_dir, out)
    generate(out)
