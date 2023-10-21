.PHONY: data clean run

venv/bin/activate: requirements.txt
	python3 -m venv venv
	./venv/bin/pip install -r requirements.txt

run: venv/bin/activate
	./venv/bin/python3 sunburst.py

clean:
	rm -rf __pycache__
	rm -rf venv
	rm -rf .ipynb_checkpoints

data:
	python3 -m src.data.import_data_pks
