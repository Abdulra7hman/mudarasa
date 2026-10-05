# ROS (and similar) PYTHONPATH entries break the venv's pytest; run everything with a clean path.
PY = env -u PYTHONPATH .venv/bin/python
RUNS ?= 3

.PHONY: setup ingest index test run eval eval-quick model-check label-sheet

setup:
	python3 -m venv .venv && .venv/bin/pip install -q -r requirements-dev.txt

ingest:
	$(PY) -m app.ingest

index:
	$(PY) -m scripts.build_index

test:
	$(PY) -m pytest -q tests

run:
	$(PY) -m uvicorn app.main:app --port 8000 --reload

model-check:
	$(PY) -m scripts.model_check

eval-quick:
	$(PY) -m eval.run --set eval/quick.jsonl --systems full --runs 1

eval:
	$(PY) -m eval.run --systems full,no_retrieval --runs $(RUNS) && $(PY) -m eval.report

label-sheet:
	$(PY) -m eval.linking.make_label_sheet
