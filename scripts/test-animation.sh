#!/bin/sh
set -eu
python3 scripts/sync_animation_manifests.py --check
LUMA_ANIMATION_TEST_DIR=$(mktemp -d)
export LUMA_ANIMATION_TEST_DIR
trap 'rm -rf "$LUMA_ANIMATION_TEST_DIR"' EXIT
./node_modules/.bin/tsc src/animation/model.ts src/animation/controller.ts src/animation/loader.ts --outDir "$LUMA_ANIMATION_TEST_DIR" --resolveJsonModule --esModuleInterop --module commonjs --target ES2022 --strict --skipLibCheck
node --test tests/animation/animation.cjs
./node_modules/.bin/tsc src/assets/base.ts src/assets/monster.ts src/entities/monsters.ts --outDir "$LUMA_ANIMATION_TEST_DIR" --resolveJsonModule --esModuleInterop --module commonjs --target ES2022 --strict --skipLibCheck
node --test tests/animation/base.cjs
./node_modules/.bin/tsc src/presentation/monsterDex.ts --outDir "$LUMA_ANIMATION_TEST_DIR" --resolveJsonModule --esModuleInterop --module commonjs --target ES2022 --strict --skipLibCheck
node --test tests/animation/monster-dex.cjs

node --test tests/animation/monster-assets.cjs
python3 scripts/sync_monster_content.py --check
node --test tests/animation/monster-content.cjs

./node_modules/.bin/tsc src/animation/pilot.ts src/animation/clock.ts src/animation/idle.ts --outDir "$LUMA_ANIMATION_TEST_DIR" --resolveJsonModule --esModuleInterop --module commonjs --target ES2022 --strict --skipLibCheck
node --test tests/animation/pilot.cjs
./node_modules/.bin/tsc tests/live/animation-clock.tsx --noEmit --resolveJsonModule --esModuleInterop --module ESNext --moduleResolution bundler --target ES2022 --jsx react-jsx --strict --skipLibCheck
node --test tests/animation/static-registry.cjs

node --test tests/animation/idle.cjs

node --test tests/animation/move.cjs

node --test tests/animation/react.cjs

node --test tests/animation/pip.cjs

node --test tests/animation/jump.cjs
