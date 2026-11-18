#!/bin/sh
set -eu

IMAGE="${IMAGE:-eight-app-suite:local}"
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CONTEXT_DIR=$(dirname "$SCRIPT_DIR")

docker build -f "$SCRIPT_DIR/Dockerfile" -t "$IMAGE" "$CONTEXT_DIR"

ENV_ARGS=""
if [ -f "$SCRIPT_DIR/.env" ]; then
  ENV_ARGS="--env-file $SCRIPT_DIR/.env"
fi

docker run --rm $ENV_ARGS \
  -p 8080:8080 \
  -p 8025:8025 \
  -p 8101:8101 \
  -p 8102:8102 \
  -p 8103:8103 \
  -p 8104:8104 \
  -p 8105:8105 \
  -p 8106:8106 \
  -p 8107:8107 \
  -p 8108:8108 \
  -p 8109:8109 \
  "$IMAGE"
