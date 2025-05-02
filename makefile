
VERSION = 0.1.0

# if version is in the form of x.y.z-dev-aaaa, set it to x.y.z-dev
ifeq ($(VERSION),$(filter $(VERSION),$(shell echo $(VERSION) | grep -E '^[0-9]+\.[0-9]+\.[0-9]+-dev-[a-z0-9]+$$')))
	VERSION := $(shell echo $(VERSION) | sed 's/-dev-[a-z0-9]*$$/-dev/')

.PHONY: all build clean client server tests

all: build

TEMP_DIR = build

WEB_SRC_TS = $(wildcard client/src/*.ts)
WEB_SRC_HTML = $(wildcard client/src/*.html)
WEB_SRC_SASS = $(wildcard client/src/*.scss)

WEB_DIST_JS = $(patsubst client/src/%.ts,mc_srv_manager/client/%.js,$(WEB_SRC_TS))
WEB_DIST_HTML = $(patsubst client/src/%.html,mc_srv_manager/client/%.html,$(WEB_SRC_HTML))
WEB_DIST_CSS = $(patsubst client/src/%.scss,mc_srv_manager/client/%.css,$(WEB_SRC_SASS))
WEB_DIST = $(WEB_DIST_JS) $(WEB_DIST_HTML) $(WEB_DIST_CSS)

SRV_SRC =  $(wildcard server/src/**/*.py) $(wildcard server/src/*.py) 
SRV_DIST = $(patsubst server/src/%,mc_srv_manager/%,$(SRV_SRC))

CONFIG_SRC = $(wildcard server/src/config.json)
CONFIG_DIST = $(patsubst server/src/%,mc_srv_manager/%,$(CONFIG_SRC))

TESTS_PY = $(wildcard tests/*.py) $(wildcard tests/**/*.py)

WHEEL = mc_srv_manager-$(VERSION)-py3-none-any.whl
ARCHIVE = mc_srv_manager-$(VERSION).tar.gz

PYPROJECT = pyproject.toml

PYTHON_PATH = $(shell if [ -d env/bin ]; then echo "env/bin/"; elif [ -d env/Scripts ]; then echo "env/Scripts/"; else echo ""; fi)
PYTHON = $(PYTHON_PATH)python

EXECUTABLE_EXTENSION = $(shell if [ -d env/bin ]; then echo ""; elif [ -d env/Scripts ]; then echo ".exe"; else echo ""; fi)

EXECUTABLE = $(PYTHON_PATH)mc-srv-manager$(EXECUTABLE_EXTENSION)

mc_srv_manager/client/%.html: client/src/%.html
	@mkdir -p $(@D)
	@echo "Copying $< to $@"
	@cp $< $@

mc_srv_manager/client/%.js: client/src/%.ts
	@mkdir -p $(@D)
	@echo "Compiling $< to $@"
	@tsc --outDir $(@D) $<

mc_srv_manager/client/%.css: client/src/%.scss
	@mkdir -p $(@D)
	@echo "Compiling $< to $@"
	@sass $< $@

mc_srv_manager/%.py: server/src/%.py
	@mkdir -p $(@D)
	@echo "Copying $< to $@"
	@cp $< $@

mc_srv_manager/%.json: server/src/%.json
	@mkdir -p $(@D)
	@echo "Copying $< to $@"
	@cp $< $@


dist/$(WHEEL): $(WEB_DIST) $(SRV_DIST) $(PYPROJECT) $(CONFIG_DIST)
	mkdir -p $(TEMP_DIR)
	$(PYTHON) build_package.py --outdir $(TEMP_DIR) --wheel --version $(VERSION)
	mkdir -p dist
	mv $(TEMP_DIR)/*.whl dist/
	rm -rf $(TEMP_DIR)
	@echo "Building wheel package complete."

dist/$(ARCHIVE): $(WEB_DIST) $(SRV_DIST) $(PYPROJECT) $(CONFIG_DIST)
	mkdir -p $(TEMP_DIR)
	$(PYTHON) build_package.py --outdir $(TEMP_DIR) --sdist --version $(VERSION)
	mkdir -p dist
	mv $(TEMP_DIR)/*.tar.gz dist/
	rm -rf $(TEMP_DIR)
	@echo "Building archive package complete."


$(EXECUTABLE) : $(WEB_DIST) $(SRV_DIST) $(PYPROJECT) $(CONFIG_DIST) dist/$(WHEEL)
	@echo "Installing package..."
	@$(PYTHON) -m pip install --upgrade --force-reinstall dist/$(WHEEL)
	@echo "Package installed."

build: dist/$(WHEEL) dist/$(ARCHIVE)
	@echo "Build complete."

clean:
	rm -rf mc_srv_manager
	rm -rf dist

client: $(WEB_DIST)
	@echo "Client build complete."

server: $(SRV_DIST) $(CONFIG_DIST)
	@echo "Server build complete."

test-report.xml: $(EXECUTABLE) $(WEB_DIST) $(SRV_DIST) $(PYPROJECT) $(CONFIG_DIST) $(TESTS_PY)
	$(PYTHON) -m pytest --junitxml=test-report.xml tests


tests: test-report.xml