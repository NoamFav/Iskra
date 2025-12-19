#!/bin/bash
set -euo pipefail

VERSION="1.7.3"
PLATFORMS=("linux-amd64" "linux-arm64" "macos-amd64" "macos-arm64")

mkdir -p releases

for platform in "${PLATFORMS[@]}"; do
    echo "Building $platform..."

    release_dir="releases/iskra-${VERSION}-${platform}"
    rm -rf "$release_dir"
    mkdir -p "$release_dir/lib" "$release_dir/bin"

    # Copy Python library
    cp -r python/src/iskra "$release_dir/lib/"

    OS="${platform%%-*}"
    ARCH="${platform##*-}"

    # Go uses 'darwin' for macOS
    if [[ "$OS" == "macos" ]]; then
        GOOS="darwin"
    else
        GOOS="$OS"
    fi

    (
        cd python/gocli
        GOOS="$GOOS" GOARCH="$ARCH" go build -o "../../$release_dir/bin/ai_commit" ./cmd/iskra
    )

    (
        cd releases
        tar -czf "iskra-${VERSION}-${platform}.tar.gz" "iskra-${VERSION}-${platform}"
        rm -rf "iskra-${VERSION}-${platform}"
    )

    echo "✓ Built $platform"
done
