.SILENT:

SHELL := /bin/bash

all: help

run:
	pyside6-project run

dist: resources icon
	pyinstaller --clean --noconfirm pixem.spec

icon:
	mkdir -p src/res/Pixem.iconset
	sips -z 16 16     src/res/logo512.png --out src/res/Pixem.iconset/icon_16x16.png
	sips -z 32 32     src/res/logo512.png --out src/res/Pixem.iconset/icon_16x16@2x.png
	sips -z 32 32     src/res/logo512.png --out src/res/Pixem.iconset/icon_32x32.png
	sips -z 64 64     src/res/logo512.png --out src/res/Pixem.iconset/icon_32x32@2x.png
	sips -z 128 128   src/res/logo512.png --out src/res/Pixem.iconset/icon_128x128.png
	sips -z 256 256   src/res/logo512.png --out src/res/Pixem.iconset/icon_128x128@2x.png
	sips -z 256 256   src/res/logo512.png --out src/res/Pixem.iconset/icon_256x256.png
	sips -z 512 512   src/res/logo512.png --out src/res/Pixem.iconset/icon_256x256@2x.png
	sips -z 512 512   src/res/logo512.png --out src/res/Pixem.iconset/icon_512x512.png
	sips -z 1024 1024 src/res/logo512.png --out src/res/Pixem.iconset/icon_512x512@2x.png
	iconutil -c icns src/res/Pixem.iconset -o src/res/Pixem.icns
	rm -rf src/res/Pixem.iconset

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
