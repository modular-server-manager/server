

.PHONY: all build clean client server tests

all: build

TEMP_DIR = build

WEB_SRC_TS = $(wildcard client/src/*.ts)
WEB_SRC_HTML = $(wildcard client/src/*.template.html)
WEB_SRC_SASS = $(wildcard client/src/*.scss)
WEB_ASSETS = $(wildcard client/src/assets/*)

WEB_DIST_JS = $(patsubst client/src/%.ts,mc_srv_manager/client/%.js,$(WEB_SRC_TS))
WEB_DIST_HTML = $(patsubst client/src/%.template.html,mc_srv_manager/client/%.html,$(WEB_SRC_HTML))
WEB_DIST_CSS = $(patsubst client/src/%.scss,mc_srv_manager/client/%.css,$(WEB_SRC_SASS))
WEB_DIST_ASSETS = $(patsubst client/src/assets/%,mc_srv_manager/client/assets/%,$(WEB_ASSETS))
WEB_DIST = $(WEB_DIST_JS) $(WEB_DIST_HTML) $(WEB_DIST_CSS) $(WEB_DIST_ASSETS)

WEB_DEV_JS = $(patsubst client/src/%.ts,client/dist/%.js,$(WEB_SRC_TS))
WEB_DEV_HTML = $(patsubst client/src/%.template.html,client/dist/%.html,$(WEB_SRC_HTML))
WEB_DEV_CSS = $(patsubst client/src/%.scss,client/dist/%.css,$(WEB_SRC_SASS))
WEB_DEV_ASSETS = $(patsubst client/src/assets/%,client/dist/assets/%,$(WEB_ASSETS))
WEB_DEV_DIST = $(WEB_DEV_JS) $(WEB_DEV_HTML) $(WEB_DEV_CSS) $(WEB_DEV_ASSETS)


SRV_SRC = $(shell find server/src -type f -name "*.py") server/src/forge/data.xml
SRV_DIST = $(patsubst server/src/%,mc_srv_manager/%,$(SRV_SRC))

CONFIG_SRC = $(wildcard server/src/config.json)
CONFIG_DIST = $(patsubst server/src/%,mc_srv_manager/%,$(CONFIG_SRC))

TESTS_PY = $(wildcard tests/*.py) $(wildcard tests/**/*.py)


# HTML TEMPLATES DEPENDENCIES
mc_srv_manager/client/account.html: client/src/metadata.template client/src/header.template
mc_srv_manager/client/dashboard.html: client/src/metadata.template client/src/header.template
mc_srv_manager/client/login.html: client/src/metadata.template




PYPROJECT = pyproject.toml

PYTHON_PATH = $(shell if [ -d env/bin ]; then echo "env/bin/"; elif [ -d env/Scripts ]; then echo "env/Scripts/"; else echo ""; fi)
PYTHON_LIB = $(shell if [ -d env/lib/python3.12/site-packages ]; then echo "env/lib/python3.12/site-packages/"; elif [ -d env/Lib/site-packages ]; then echo "env/Lib/site-packages/"; else echo ""; fi)
PYTHON = $(PYTHON_PATH)python

EXECUTABLE_EXTENSION = $(shell if [ -d env/bin ]; then echo ""; elif [ -d env/Scripts ]; then echo ".exe"; else echo ""; fi)

EXECUTABLE = $(PYTHON_PATH)mc-srv-manager$(EXECUTABLE_EXTENSION)

# if not defined, get the version from git
VERSION ?= $(shell $(PYTHON) get_version.py)

# if version is in the form of x.y.z-dev-aaaa or x.y.z-dev+aaaa, set it to x.y.z-dev
# VERSION_STR = $(shell echo $(VERSION) | sed 's/-dev-[a-z0-9]*//')
VERSION_STR = $(shell echo $(VERSION) | sed 's/-dev-[a-z0-9]*//; s/-dev+.*//')


WHEEL = mc_srv_manager-$(VERSION_STR)-py3-none-any.whl
ARCHIVE = mc_srv_manager-$(VERSION_STR).tar.gz


$(PYTHON_LIB)/build:
	$(PYTHON_PATH)pip install build


print-%:
	@echo $* = $($*)

mc_srv_manager/client/%.html: client/src/%.template.html
	@mkdir -p $(@D)
	@echo "Compiling $< to $@"
	@python html_template.py client/src $(subst .template.html,,$(subst client/src/,,$<)) -o $@

mc_srv_manager/client/%.js: client/src/%.ts
	@mkdir -p $(@D)
	@echo "Compiling $< to $@"
	@tsc --outDir $(@D) $< --module es6 --target es6 --strict --sourceMap

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

mc_srv_manager/client/assets/%: client/src/assets/%
	@mkdir -p $(@D)
	@echo "Copying $< to $@"
	@cp $< $@

mc_srv_manager/%: server/src/%
	@mkdir -p $(@D)
	@echo "Copying $< to $@"
	@cp $< $@

dist/mc_srv_manager-0.1.0-py3-none-any.whl: $(WEB_DIST) $(SRV_DIST) $(PYPROJECT) $(CONFIG_DIST) $(PYTHON_LIB)/build
	$(PYTHON) -m build --outdir dist
	@echo "Building wheel package complete."

dist/$(ARCHIVE): $(WEB_DIST) $(SRV_DIST) $(PYPROJECT) $(CONFIG_DIST) $(PYTHON_LIB)/build
	mkdir -p $(TEMP_DIR)
	$(PYTHON) build_package.py --outdir $(TEMP_DIR) --sdist --version $(VERSION_STR)
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


client: $(WEB_DIST)
	@echo "Client build complete."

server: $(SRV_DIST) $(CONFIG_DIST)
	@echo "Server build complete."

test-report.xml: $(EXECUTABLE) $(WEB_DIST) $(SRV_DIST) $(PYPROJECT) $(CONFIG_DIST) $(TESTS_PY)
	$(PYTHON) -m pytest --junitxml=test-report.xml tests


install: $(EXECUTABLE)

start: $(EXECUTABLE)
	@echo "Starting server..."
	@$(EXECUTABLE) --module-level all:TRACE --module-level http_server:DEBUG --log-file server.log:TRACE -c /var/minecraft/config.json


tests: clean-tests test-report.xml



# client dev
client/dist/%.js: client/src/%.ts
	@mkdir -p $(@D)
	@echo "Compiling $< to $@"
	@tsc --outDir $(@D) $< --module es6 --target es6 --strict

client/dist/%.css: client/src/%.scss
	@mkdir -p $(@D)
	@echo "Compiling $< to $@"
	@sass $< $@

client/dist/assets/%: client/src/assets/%
	@mkdir -p $(@D)
	@echo "Copying $< to $@"
	@cp $< $@

client/dist/%.html: client/src/%.template.html
	@mkdir -p $(@D)
	@echo "Compiling $< to $@"
	@python html_template.py client/src $(subst .template.html,,$(subst client/src/,,$<)) -o $@


client-dev: $(WEB_DEV_DIST)
	@echo "Client dev build complete."
	@npm run start --prefix client

client-dev-clean:
	rm -rf client/dist


clean:
	rm -rf mc_srv_manager
	rm -rf dist

clean-tests:
	rm -rf test-report.xml

clean-all: client-dev-clean clean clean-tests
