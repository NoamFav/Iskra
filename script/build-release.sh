#!/bin/bash
set -euo pipefail

VERSION="${1:-$(git describe --tags --abbrev=0 2>/dev/null || echo "dev")}"
PLATFORMS=("linux-amd64" "linux-arm64" "macos-amd64" "macos-arm64")

echo "Building Iskra $VERSION..."
mkdir -p releases

for platform in "${PLATFORMS[@]}"; do
    echo "  Building $platform..."

    release_dir="releases/iskra-${VERSION}-${platform}"
    rm -rf "$release_dir"
    mkdir -p "$release_dir"

    OS="${platform%%-*}"
    ARCH="${platform##*-}"

    case "$OS" in
        macos) GOOS="darwin" ;;
        *)     GOOS="$OS" ;;
    esac

    case "$ARCH" in
        amd64) GOARCH="amd64" ;;
        arm64) GOARCH="arm64" ;;
    esac

    (
        cd go-core
        GOOS="$GOOS" GOARCH="$GOARCH" go build \
            -ldflags="-s -w -X main.Version=${VERSION}" \
            -o "../$release_dir/iskra" \
            ./cmd/iskra/
    )

    cp script/install.sh "$release_dir/"

    (
        cd releases
        tar -czf "iskra-${VERSION}-${platform}.tar.gz" "iskra-${VERSION}-${platform}"
        rm -rf "iskra-${VERSION}-${platform}"
    )

    echo "  ✓ $platform"
done

echo ""
echo "Release artifacts:"
ls -lh releases/*.tar.gz
