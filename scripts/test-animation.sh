#!/bin/sh
set -eu
LUMA_ANIMATION_TEST_DIR=$(mktemp -d)
export LUMA_ANIMATION_TEST_DIR
trap 'rm -rf "$LUMA_ANIMATION_TEST_DIR"' EXIT
./node_modules/.bin/tsc src/animation/model.ts src/animation/controller.ts src/animation/loader.ts --outDir "$LUMA_ANIMATION_TEST_DIR" --resolveJsonModule --esModuleInterop --module commonjs --target ES2022 --strict --skipLibCheck
node --test tests/animation/animation.cjs
./node_modules/.bin/tsc src/assets/base.ts src/entities/monsters.ts --outDir "$LUMA_ANIMATION_TEST_DIR" --resolveJsonModule --esModuleInterop --module commonjs --target ES2022 --strict --skipLibCheck
node --test tests/animation/base.cjs
./node_modules/.bin/tsc src/presentation/monsterDex.ts --outDir "$LUMA_ANIMATION_TEST_DIR" --resolveJsonModule --esModuleInterop --module commonjs --target ES2022 --strict --skipLibCheck
node --test tests/animation/monster-dex.cjs
