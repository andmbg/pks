.PHONY: data clean run

venv_activate = . venv/bin/activate
python = $(venv_activate) && python3

install: requirements.txt
	python3 -m venv venv
	./venv/bin/pip install -r requirements.txt

run: venv/bin/activate
	$(python) -m pks.dashboard

clean:
	rm -rf __pycache__
	rm -rf venv
	rm -rf .ipynb_checkpoints

data:
	$(python) -m pks.src.data.import_data_pks
