.PHONY: run test gen-ifc docker frontend

run:
	./run.sh

test:
	python3 backend/test_api.py

gen-ifc:
	python3 backend/scripts/generate_sample_ifc_fallback.py --out sample-ifc/BIMGuard_Demo.ifc

docker:
	docker compose up --build

frontend:
	cd frontend && npm install --registry https://registry.npmmirror.com && npm run dev

build:
	cd frontend && npm run build

health:
	curl -s http://localhost:8000/api/health | python3 -m json.tool

summary:
	curl -s "http://localhost:8000/api/summary?min_width=750" | python3 -m json.tool
