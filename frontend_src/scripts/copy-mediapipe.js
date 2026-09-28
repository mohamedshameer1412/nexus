// Copies the face-detector runtime (WebAssembly) from node_modules to public/, so it is served from our own origin (nothing loads from a CDN).
// The small model file public/mediapipe/blaze_face_short_range.tflite is committed to the repository.
const fs = require("fs");
const path = require("path");
const from = path.join(__dirname, "..", "node_modules", "@mediapipe", "tasks-vision", "wasm");
const to = path.join(__dirname, "..", "public", "mediapipe", "wasm");
if (!fs.existsSync(from)) process.exit(0);
fs.mkdirSync(to, { recursive: true });
for (const f of ["vision_wasm_internal.js", "vision_wasm_internal.wasm", "vision_wasm_nosimd_internal.js", "vision_wasm_nosimd_internal.wasm"]) fs.copyFileSync(path.join(from, f), path.join(to, f));
