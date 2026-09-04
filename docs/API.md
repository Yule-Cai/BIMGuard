# API Reference — BIMGuard

Base: `http://localhost:8000` — interactive docs at `/docs` (Swagger) and `/redoc`

## Health

`GET /api/health` → `{status, model_loaded, current_file}`

## Upload

`POST /api/upload` — `multipart/form-data` with field `file=@model.ifc`

Response: `{filename, path, counts: {IfcDoor, IfcWall, ...}, message}`

Errors: `400` if not `.ifc` or parse fails.

## Summary (both rules)

`GET /api/summary?min_width=750`

```json
{
  "min_width": 750,
  "score": 36,
  "doors": {"total":3,"passed":2,"failed":1,"results":[...]},
  "clashes": {"count":1,"results":[...]},
  "rule": "HK FS Code 2011 Table B2"
}
```

Door result: `{guid,name,tag,measured_mm,required_mm,delta_mm,status,rule,type}`  
Clash result: `{a_guid,a_name,a_type,b_guid,b_name,b_type,penetration_mm,severity}`

## Single-rule

- `GET /api/doors?min_width=750` → `{results: [...]}`
- `GET /api/clashes` → `{results, count}`

## Elements

- `GET /api/elements?type=IfcDoor&limit=50&guid=...` → `{elements: [{guid,name,tag,type,width,placement}], count}`
- `GET /api/element/{guid}` → `{guid, psets, info}`

## Chat (tool-router)

`POST /api/chat` — JSON `{message, min_width=750, use_llm=false}`

Response: `{reply, tools_used: [...], mode: "mock_deterministic"|"llm:gpt-4o-mini", evidence?}`

Examples:
```bash
curl -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" \
  -d '{"message":"Why is D-102 a problem?","min_width":750}'

curl -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" \
  -d '{"message":"Show me all serious violations","min_width":850,"use_llm":true}'
```

When `use_llm=false` (default) or no `OPENAI_API_KEY`, mock router still calls tools and returns templated evidence.

## Direct tools (debug)

`POST /api/tools/{tool_name}` with JSON payload, e.g. `{"min_width":750}` for `check_exit_door_width`

Available: `check_exit_door_width`, `detect_clashes`, `get_summary`, `get_ifc_elements`, `get_element_properties`

## Static

- `GET /` → `frontend/static.html` (or `frontend/dist/index.html` if built)
- `GET /app` → React dist
- `GET /sample-ifc/BIMGuard_Demo.ifc` → download sample
