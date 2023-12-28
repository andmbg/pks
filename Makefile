.PHONY: data clean run

install: requirements.txt
	python3 -m venv venv
	./venv/bin/pip install -r requirements.txt

run: venv/bin/activate
	./venv/bin/python3 -m pks.dashboard

clean:
	rm -rf __pycache__
	rm -rf venv
	rm -rf .ipynb_checkpoints

data:
	./venv/bin/python3 -m pks.src.data.import_data_pks
