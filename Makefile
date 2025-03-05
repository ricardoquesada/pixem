.SILENT:

SHELL := /bin/bash

all: help

run: resources
	python3 src/main.py

dist: resources
	pyinstaller --name Pixem src/main.py


resources:
	pyside6-rcc src/resources.qrc -o src/resources_rc.py

venv:
	rm -rf venv
	python3 -m venv venv
	source venv/bin/activate && pip install -r requirements.txt

format:
	black --line-length=100 *.py

lint:
	ruff check --line-length=100 --fix *.py

clean:
	rm -f src/resources_rc.py
	rm -rf venv
	rm -rf dist

help:
	echo "Options: run, resources, venv, format, clean"
