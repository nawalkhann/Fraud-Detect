PY ?= python3
export PYTHONPATH := src

.PHONY: install test data report

install:
	$(PY) -m pip install -e ".[dev]"

test:
	$(PY) -m pytest -q

data:            ## download (needs KAGGLE_USERNAME/KAGGLE_KEY) and prepare splits
	$(PY) -m fraud.data download $(if $(ZIP),--zip $(ZIP))
	$(PY) -m fraud.data prepare

report:
	$(PY) -m fraud.profile
