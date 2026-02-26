.PHONY: build install clean release lint

VERSION := $(shell git describe --tags --always 2>/dev/null || echo "dev")
LDFLAGS := -s -w -X main.version=$(VERSION)
BIN     := bin/iskra
SRC     := go-core/cmd/iskra/

build:
	@echo "→ Building iskra $(VERSION)"
	@cd go-core && go build -ldflags "$(LDFLAGS)" -o ../$(BIN) ./cmd/iskra/
	@echo "✓ $(BIN)"

install: build
	@cp $(BIN) ~/.local/bin/iskra
	@echo "✓ Installed to ~/.local/bin/iskra"

lint:
	@cd go-core && go vet ./...

clean:
	@rm -f $(BIN)

# Build all release targets locally (requires Docker or cross-compile toolchain)
release-local:
	@mkdir -p releases
	@for target in \
		linux/amd64 \
		linux/arm64 \
		darwin/amd64 \
		darwin/arm64; do \
		os=$$(echo $$target | cut -d/ -f1); \
		arch=$$(echo $$target | cut -d/ -f2); \
		osname=$$os; [ "$$os" = "darwin" ] && osname="macos"; \
		echo "→ Building $$osname-$$arch"; \
		cd go-core && GOOS=$$os GOARCH=$$arch CGO_ENABLED=0 \
			go build -ldflags "$(LDFLAGS)" -o ../releases/iskra ./cmd/iskra/ && cd ..; \
		tar -czf releases/iskra-$(VERSION)-$$osname-$$arch.tar.gz -C releases iskra; \
		rm releases/iskra; \
		echo "✓ releases/iskra-$(VERSION)-$$osname-$$arch.tar.gz"; \
	done

help:
	@echo "iskra build targets:"
	@echo "  make build          Build binary to bin/iskra"
	@echo "  make install        Build and install to ~/.local/bin/iskra"
	@echo "  make lint           Run go vet"
	@echo "  make clean          Remove built binary"
	@echo "  make release-local  Build all platform tarballs to releases/"
