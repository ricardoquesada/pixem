.SILENT:

SHELL := /bin/bash

all: help

run:
	pyside6-project run

dist: resources
	pyinstaller --name Pixem src/main.py


resources:
	pyside6-rcc src/resources.qrc -o src/rc_resources.py

lupdate: clean
	lupdate ./src/*.py -ts translations/pixem_en.ts


venv:
	rm -rf venv
	python3 -m venv venv
	source venv/bin/activate && pip install -r requirements.txt

format:
	black --line-length=100 *.py

lint:
	ruff check --line-length=100 --fix *.py

clean:
	pyside6-project clean
	rm -rf venv
	rm -rf dist

help:
	echo "Options: run, resources, venv, format, clean"
