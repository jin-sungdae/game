#!/bin/sh
set -eu
LUMA_PRESENTATION_TEST_DIR=$(mktemp -d)
export LUMA_PRESENTATION_TEST_DIR
trap 'rm -rf "$LUMA_PRESENTATION_TEST_DIR"' EXIT
./node_modules/.bin/tsc src/presentation/model.ts src/presentation/baseMotion.ts --outDir "$LUMA_PRESENTATION_TEST_DIR" --module commonjs --target ES2022 --strict --skipLibCheck
node --test tests/presentation/visual.cjs
node --test tests/presentation/base-motion.cjs
