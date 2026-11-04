.PHONY: install test test-ui audit generate run verify verify-omnibrain verify-live bootstrap docker clean

install:
	python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

test:
	.venv/bin/python -m pytest -q --junitxml=test-results/junit.xml

test-ui:
	npm ci --no-audit --no-fund --ignore-scripts
	node --test tests/test_web_ui.test.js tests/test_web_ui_dom.test.js

audit:
	.venv/bin/python scripts/audit_dependencies.py

generate:
	.venv/bin/python scripts/gen_profiles.py

verify:
	.venv/bin/python scripts/verify_offline.py

verify-omnibrain:
	.venv/bin/python scripts/verify_omnibrain_contract.py

verify-live:
	.venv/bin/python scripts/verify_providers_live.py

bootstrap:
	./scripts/bootstrap_remote.sh --check

run:
	.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

docker:
	docker compose up --build -d

clean:
	rm -rf .pytest_cache test-results/*.xml
