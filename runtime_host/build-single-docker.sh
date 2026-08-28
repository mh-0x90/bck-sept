#!/bin/sh
set -eu
IMAGE="${IMAGE:-eight-app-suite:local}"
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CONTEXT_DIR=$(dirname "$SCRIPT_DIR")
docker build -f "$SCRIPT_DIR/Dockerfile" -t "$IMAGE" "$CONTEXT_DIR"
