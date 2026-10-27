# Live2D technical selection

- l2d 2.1.1: framework-free wrapper (MIT); Cubism Core remains under its own terms. Uses public init/load/playMotion/setExpression/setPosition/setScale/setParams/getParams/destroy APIs. Observed Core version will be recorded in the verification report.
- l2d-widget 0.1.2: unsuitable website-tip lifecycle, would duplicate controls. No new widget subsystem.
- pixi-live2d-display 0.4.0: older Pixi 6 peer stack; not installed.
- Open-LLM-VTuber: useful architectural reference, but its extra server/AI/ASR/TTS stack would duplicate the application's services. Not installed.
- Offline TTS: existing comtypes/SAPI5 service extended with real Viseme events and its COM apartment message pump. Voice selection is independent per character. No models downloaded.

## ESM packaging compatibility

The pinned ESM bundle inserts its old Cubism 2 script element before adding text. On the tested Chromium path this left AMotion undefined. The adapter preloads the exact embedded script through a same-origin script URL before importing the unchanged ESM bundle. No vendor source is patched. Both private scripts are pinned by SHA-256. Only the renderer child permits SDK-required inline initialization and WASM compilation; it denies network destinations outside self and cannot be framed cross-origin. The main application remains X-Frame-Options DENY. Imported model files cannot contain JavaScript.

For local development only, the embedded string can be decoded as data (not evaluated) from the installed official npm bundle:

```python
import json
from pathlib import Path
raw = Path('node_modules/l2d/dist/index.js').read_text(encoding='utf8')
start = raw.index('t.append(') + len('t.append(')
core, _ = json.JSONDecoder(strict=False).raw_decode(raw[start:])
# Write original UTF-8 bytes to the approved private runtime directory.
# Never run this on imported model data; never execute expressions as Python.
Path('cubism2.js').write_bytes(core.encode('utf8'))
```

Runtime hashes: l2d ESM 7e2da1360a2d58515343f2dfe5b42dd772588c3a96580b5bbf2f90eeb4496d1e; old Core 612ac06fc888c193ffe432831ffb3831729967b20cc944b3dc6dc96328bbd2ad. Licensing information: https://www.live2d.com/en/sdk/license/ and https://www.live2d.com/en/sdk/license/expandable/ . Editor workflow: https://docs.live2d.com/en/cubism-editor-manual/psd-import/ and https://docs.live2d.com/en/cubism-editor-manual/export-moc3-motion3-files/ .

## Personal model authoring result

The two private half-body rigs were built from generated, separated layers by Wzhang3912/image2live2d (Apache-2.0, commit 714e7cc9191f1ef6c9a1732c80e8b566ec127d6b). Its native MOC3 writer, atlas builder, semantic mesh and parameter authoring were used without patching vendor source. The official Cubism Core 6.0.1 actually loaded and rendered both bundles. A Cubism Editor .cmo3 was not produced; the editable layer source and IRR are preserved privately. The personal assets and proprietary SDK stay outside the public application packages.

