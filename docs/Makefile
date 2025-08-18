SHELL := /bin/bash
SOURCEDIR = source
BUILDDIR = build

all: apidoc
	sphinx-build -M html "$(SOURCEDIR)" "$(BUILDDIR)" -W --keep-going

apidoc: clean-apidoc
	sphinx-apidoc --private --module-first --force \
      --output-dir "$(SOURCEDIR)/api" \
      ../src/l1000geom ../src/l200geom/_version.py

clean-apidoc:
	rm -rf "$(SOURCEDIR)/api"

clean: clean-apidoc
	rm -rf "$(BUILDDIR)"
