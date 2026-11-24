# Build, package and deploy the app.

VERSION       ?= 0.0.3
SESSION_IMAGE ?= semverex-session
DEEPSEEK      ?= deepseek


SHELL := /bin/bash
.ONESHELL:
.PHONY: help build test run bump clean build-session start-session

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-16s %s\n", $$1, $$2}'

build: $(BIN) ## Compile the binary locally

$(BIN): $(SOURCES)


test: ## Run unit tests

run: ## Run locally (dev mode)

bump: gitleaks ## Bump VERSION (Makefile) and the image tag (deploy/deployment.yaml)
	@read -p 'Next version: ' -e -i "$(VERSION)" NEXT_VERSION
	if [ "$(VERSION)" == "$$NEXT_VERSION" ]; then
		echo "Error: same version"
		exit 1
	fi
	sed -i -E 's|^(VERSION[[:space:]]*\?=[[:space:]]*).*|\1'"$$NEXT_VERSION"'|' Makefile
	git commit -m "Bump version $$NEXT_VERSION" Makefile
	git tag $$NEXT_VERSION

release:
	git push origin main
	git push --tags

gitleaks: ## Avoid secrets to leak
	gitleaks git && gitleaks dir

install: build

clean: ## Remove local build files

build-session: ## Build the session container (host-user dev environment with SESSION.md as session context)
	docker build -t $(SESSION_IMAGE) $(BUILD_SESSION_EXTRA_PARAMS) \
		--build-arg UID=$$(id -u) --build-arg GID=$$(id -g) \
		-f Dockerfile.session .

start-session: ## Start a DeepSeek Coder session with SESSION.md as the initial context (no memory limit)
	docker run -it --rm \
		--memory 0 --memory-swap -1 \
		-e DEEPSEEK_API_KEY="$$(op item get DEEPSEEK_API_KEY --vault Employee --format json | jq -r '.fields[]|select(.id=="credential").value')" \
		-u $$(id -u):$$(id -g) \
		-v "$$PWD:/workspace" -w /workspace \
		$(SESSION_IMAGE) $(DEEPSEEK) "Read /workspace/SESSION.md as the initial session context, then wait for instructions."
