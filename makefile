
.PHONY: all build clean install client server

all: dist/mc_srv_manager-0.1.0-py3-none-any.whl

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

PYPROJECT = pyproject.toml

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


dist/mc_srv_manager-0.1.0-py3-none-any.whl: $(WEB_DIST) $(SRV_DIST) $(PYPROJECT) $(CONFIG_DIST)
	python3 -m build --outdir dist
	@echo "Building wheel package complete."

install : $(WEB_DIST) $(SRV_DIST) $(PYPROJECT) $(CONFIG_DIST)
	@echo "Installing package..."
	@pip install .
	@echo "Package installed."

build: dist/mc_srv_manager-0.1.0-py3-none-any.whl

clean:
	rm -rf mc_srv_manager
	rm -rf dist

client: $(WEB_DIST)
	@echo "Client build complete."

server: $(SRV_DIST) $(CONFIG_DIST)
	@echo "Server build complete."