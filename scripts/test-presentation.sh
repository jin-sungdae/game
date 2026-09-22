#!/bin/sh
set -eu
LUMA_PRESENTATION_TEST_DIR=$(mktemp -d)
export LUMA_PRESENTATION_TEST_DIR
trap 'rm -rf "$LUMA_PRESENTATION_TEST_DIR"' EXIT
./node_modules/.bin/tsc src/presentation/model.ts src/presentation/baseMotion.ts src/presentation/evolution.ts src/presentation/items.ts --outDir "$LUMA_PRESENTATION_TEST_DIR" --module commonjs --target ES2022 --strict --skipLibCheck
node --test tests/presentation/visual.cjs
node --test tests/presentation/base-motion.cjs
node --test tests/presentation/evolution.cjs
node --test tests/presentation/items.cjs
./node_modules/.bin/tsc src/components/ItemInteraction.tsx --outDir "$LUMA_PRESENTATION_TEST_DIR" --module commonjs --target ES2022 --jsx react-jsx --strict --skipLibCheck
NODE_PATH="$PWD/node_modules" node --test tests/presentation/item-ui.cjs
./node_modules/.bin/tsc src/components/CollectionDex.tsx --outDir "$LUMA_PRESENTATION_TEST_DIR" --resolveJsonModule --esModuleInterop --module commonjs --target ES2022 --jsx react-jsx --strict --skipLibCheck
NODE_PATH="$PWD/node_modules" node --test tests/presentation/collection-dex.cjs
