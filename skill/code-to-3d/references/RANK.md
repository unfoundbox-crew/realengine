# Engine rank (code-to-3d)

1. Local deterministic first: seeded bpy build, local Three.js.
2. Checked-in presets over generated assets; pin every seed.
3. On-device readers (zero-vision/OCR) before any pixel upload.
4. Cloud render only when the human names the engine out loud.
5. Never silent cloud: no background API calls, no quiet fallbacks.
6. Every cloud step is logged in the build receipt with cost.
7. If local can do it slower, local still wins by default.
8. Taste questions go to the human eye, never to a paid model.
9. A missing engine fails closed with a message, not a retry loop.
10. Receipts carry engine + seed so any render reproduces bit-exact.
11. New engines enter at the bottom after a local-versus-cloud check.
12. Benchmarks are measured here, never quoted from a README.
13. Weights without a local runtime are treated as absent.
14. Free-tier minutes are a budget line, not an excuse to skip local.
15. When in doubt, ask: one plain question, cost attached.
