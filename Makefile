.SILENT:

SHELL := /bin/bash

all: help

run:
	pyside6-project run

dist: resources
	pyinstaller --name Pixem src/main.py

resources:
	pyside6-rcc src/res/resources.qrc -o src/res/rc_resources.py

lupdate:
	pyside6-lupdate ./src/*.py -ts src/res/translations/**/*.ts

lrelease:
	pyside6-lrelease ./src/res/translations/**/*.ts

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

purge: clean
	rm -rf venv
	rm -rf dist

help:
	echo "Options: run, resources, venv, format, clean"
