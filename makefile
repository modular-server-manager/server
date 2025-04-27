
.PHONY: all build clean install client server

all: dist/mc_srv_manager-0.1.0-py3-none-any.whl

WEB_SRC_TS = $(wildcard client/src/*.ts)
WEB_SRC_HTML = $(wildcard client/src/*.html)
WEB_SRC_SASS = $(wildcard client/src/*.scss)

WEB_DIST_JS = $(patsubst client/src/%.ts,mc_srv_manager/client/%.js,$(WEB_SRC_TS))
WEB_DIST_HTML = $(patsubst client/src/%.html,mc_srv_manager/client/%.html,$(WEB_SRC_HTML))
WEB_DIST_CSS = $(patsubst client/src/%.scss,mc_srv_manager/client/%.css,$(WEB_SRC_SASS))
WEB_DIST = $(WEB_DIST_JS) $(WEB_DIST_HTML) $(WEB_DIST_CSS)

SRV_SRC = $(wildcard server/src/*)
SRV_DIST = $(patsubst server/src/%,mc_srv_manager/%,$(SRV_SRC))

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


dist/mc_srv_manager-0.1.0-py3-none-any.whl: $(WEB_DIST) $(SRV_DIST) $(PYPROJECT) 
	python3 -m build --outdir dist
	@echo "Building wheel package complete."

install : $(WEB_DIST) $(SRV_DIST) $(PYPROJECT)
	@echo "Installing package..."
	@pip install .
	@echo "Package installed."

clean:
	rm -rf mc_srv_manager
	rm -rf dist

client: $(WEB_DIST)
	@echo "Client build complete."

server: $(SRV_DIST)
	@echo "Server build complete."