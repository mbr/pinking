PY_FILES = $(shell find . -name \*.py -print)
PEX_FILE = pk.pex

$(PEX_FILE): $(PY_FILES)
	pex -s . -p $@ -v -e pinking.cli:main

clean:
	rm -f $(PEX_FILE)

.PHONY: clean
