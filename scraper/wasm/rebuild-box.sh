#!/bin/sh
# Required production build: all four Engine map sources execute inside WASM.
# No plaintext-JS or V8-bytecode runtime is used or generated here.
set -eu
DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/../.." && pwd)"
BOX="$DIR/box"
: "${QJS_SRC:?Set QJS_SRC to the quickjs-ng v0.17.0 source checkout}"
export QJS_SRC
for src in function.js normalize.js sourceMap.js sourceMapper.js; do
  test -f "$ROOT/engine/MonoSyllabism/mapbuilder/base/$src" || {
    echo "Missing Engine build input: $src" >&2; exit 1;
  }
done
test -f "$ROOT/engine/knowledge/isTreasure/master.json"
python3 -m ziglang version
if [ ! -d "$BOX/node_modules/javascript-obfuscator" ]; then
  npm ci --prefix "$BOX" --no-audit --no-fund
fi
sh "$BOX/tools/build-engine.sh"
(cd "$BOX" && node build-payload.mjs && node tools/pack-box.mjs)
node "$BOX/tools/record-build.mjs"
