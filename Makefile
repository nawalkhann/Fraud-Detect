PY ?= python3
export PYTHONPATH := src

.PHONY: install test data data-ulb report train serve dashboard drift docker website

install:
	$(PY) -m pip install -e ".[dev]"

test:
	$(PY) -m pytest -q

data:            ## download (needs KAGGLE_USERNAME/KAGGLE_KEY) and prepare splits
	$(PY) -m fraud.data download $(if $(ZIP),--zip $(ZIP))
	$(PY) -m fraud.data prepare

data-ulb:        ## ULB card data (needs Kaggle token, or CSV=path/to/creditcard.csv)
	$(PY) -m fraud.ulb download $(if $(CSV),--csv $(CSV))
	$(PY) -m fraud.ulb prepare

report:
	$(PY) -m fraud.profile --dataset ieee
	$(PY) -m fraud.profile --dataset ulb

train:           ## train, tune threshold on valid, report errors on train/valid/test
	$(PY) -m fraud.train --dataset ieee
	$(PY) -m fraud.train --dataset ulb

serve:           ## scoring API on :8000 (DATASET=ieee|ulb)
	FRAUD_DATASET=$(or $(DATASET),ieee) $(PY) -m uvicorn fraud.api:app --port 8000

dashboard:       ## analyst alert queue on :8501
	$(PY) -m streamlit run app/dashboard.py

drift:           ## BATCH=recent.parquet DATASET=ieee|ulb; exits 1 on drift
	$(PY) -m fraud.drift --dataset $(or $(DATASET),ieee) --batch $(BATCH)

docker:
	docker compose up --build

website:
	python3 website/build.py
