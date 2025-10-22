.PHONY: all build clean server tests

all: build

TEMP_DIR = build

WEB_DEV_DIST = $(WEB_DEV_JS) $(WEB_DEV_HTML) $(WEB_DEV_CSS) $(WEB_DEV_ASSETS)


SRV_SRC = $(shell find server/src -type f -name "*.py") server/src/minecraft/properties.xml server/src/bus/events.xml server/src/events_descriptions.json
SRV_DIST = $(patsubst server/src/%,modular_server_manager/%,$(SRV_SRC))

CONFIG_SRC = $(wildcard server/src/config.json)
CONFIG_DIST = $(patsubst server/src/%,modular_server_manager/%,$(CONFIG_SRC))

TESTS_PY = $(wildcard tests/*.py) $(wildcard tests/**/*.py)


PYPROJECT = pyproject.toml

PYTHON_PATH = $(shell if [ -d env/bin ]; then echo "env/bin/"; elif [ -d env/Scripts ]; then echo "env/Scripts/"; else echo ""; fi)
PYTHON_LIB = $(shell find env/lib -type d -name "site-packages" | head -n 1; if [ -d env/Lib/site-packages ]; then echo "env/Lib/site-packages/"; fi)
PYTHON = $(PYTHON_PATH)python

EXECUTABLE_EXTENSION = $(shell if [ -d env/bin ]; then echo ""; elif [ -d env/Scripts ]; then echo ".exe"; else echo ""; fi)

APP_EXECUTABLE = $(PYTHON_PATH)modular-server-manager$(EXECUTABLE_EXTENSION)

# if not defined, get the version from git
VERSION ?= $(shell $(PYTHON) get_version.py)

# if version is in the form of x.y.z-dev-aaaa or x.y.z-dev+aaaa, set it to x.y.z-dev
VERSION_STR = $(shell echo $(VERSION) | sed "s/-dev-[a-z0-9]*//; s/-dev+.*//")


WHEEL = modular_server_manager-$(VERSION_STR)-py3-none-any.whl
ARCHIVE = modular_server_manager-$(VERSION_STR).tar.gz

$(PYTHON_LIB)/build:
	$(PYTHON_PATH)pip install build


print-%:
	@echo $* = $($*)

modular_server_manager/%.py: server/src/%.py
	@mkdir -p $(@D)
	@echo "Copying $< to $@"
	@cp $< $@

modular_server_manager/%.json: server/src/%.json
	@mkdir -p $(@D)
	@echo "Copying $< to $@"
	@cp $< $@

modular_server_manager/%: server/src/%
	@mkdir -p $(@D)
	@echo "Copying $< to $@"
	@cp $< $@

dist:
	mkdir -p dist

dist/$(WHEEL): $(SRV_DIST) $(PYPROJECT) $(CONFIG_DIST) $(PYTHON_LIB)/build dist
	mkdir -p $(TEMP_DIR)
	$(PYTHON) build_package.py --outdir $(TEMP_DIR) --wheel --version $(VERSION_STR)
	mkdir -p dist
	mv $(TEMP_DIR)/*.whl dist/$(WHEEL)
	rm -rf $(TEMP_DIR)
	@echo "Building wheel package complete."

dist/$(ARCHIVE): $(SRV_DIST) $(PYPROJECT) $(CONFIG_DIST) $(PYTHON_LIB)/build dist
	mkdir -p $(TEMP_DIR)
	$(PYTHON) build_package.py --outdir $(TEMP_DIR) --sdist --version $(VERSION_STR)
	mkdir -p dist
	mv $(TEMP_DIR)/*.tar.gz dist/$(ARCHIVE)
	rm -rf $(TEMP_DIR)
	@echo "Building archive package complete."

$(APP_EXECUTABLE) : dist/$(WHEEL)
	@echo "Installing package..."
	@$(PYTHON) -m pip install --upgrade --force-reinstall dist/$(WHEEL)
	@echo "Package installed."

build: dist/$(WHEEL) dist/$(ARCHIVE)

server: $(SRV_DIST) $(CONFIG_DIST)



test-report.xml: $(APP_EXECUTABLE) $(SRV_DIST) $(PYPROJECT) $(CONFIG_DIST) $(TESTS_PY)
	$(PYTHON) -m pytest --junitxml=test-report.xml tests


install: $(APP_EXECUTABLE)

start: install
	@$(APP_EXECUTABLE) \
		-c /var/minecraft/config.json \
		--log-file server.trace.log:TRACE \
		--log-file server.debug.log:DEBUG \
		--module-level config:DEBUG \
		--module-level minecraft.properties:DEBUG

tests: clean-tests test-report.xml


clean:
	rm -rf modular_server_manager
	rm -rf dist
	rm -rf $(PYTHON_LIB)/modular_server_manager
	rm -rf $(PYTHON_LIB)/modular_server_manager-*.dist-info
	rm -rf $(APP_EXECUTABLE)

clean-tests:
	rm -rf test-report.xml

clean-all: client-dev-clean clean clean-tests
