# 2.10.3 daily-use repair

This pass keeps the existing assistant, Action Registry, TaskManager, Live2D renderer and provider routes. It adds no Agent or model service.

- Dialogue is stored under the existing private AI data root, partitioned by project, persona and logical model reference. Search and restart restoration are local. Recent successful discussion is bounded by the existing roleplay context-budget helper (12 candidate turns, approximately 10,000 characters); it is untrusted discussion, not Canon or approval. Pending operations are never automatically restored or executed.
- Complete single Chinese UI commands use the existing typed Action/permission/receipt path. Compound, ambiguous or writing requests continue to the selected AI. The result explicitly identifies LOCAL_ACTION. No implicit cross-provider fallback.
- Windows offline SAPI recognition shares the existing speech COM worker. Capture starts only on request, ends after one result/timeout/stop, uses an owner and recognition ID, and stores no microphone audio. Low-confidence results require manual review even when automatic sending is selected. Text works if ASR/TTS fails. Reply TTS remains opt-in and uses the per-character system voice and actual viseme events. These are synthetic system voices, not the original voice actors.
- Existing private v5 meshes are unchanged. A frontal raster, face sheet, mesh JSON and compiled MOC3 are not a production-quality layered Cubism project. No PSD/PSB/CMO3/CAN3 was found in the authorized companion source tree. Shoulder, elbow, wrist, hand, side-face and hidden clothing/axilla surfaces are insufficient for the requested gestures. New motion names would not fix this.

## Art repair gate

Before claiming improved character art, provide a consistent layered illustration with hidden regions painted, independent eyes/eyelids/irises/mouth parts, head angles, torso/neck/shoulder/upper arm/forearm/wrist/hands, coherent sleeve and hair overlaps. Build and inspect deformation across angles and actual task poses, preserve editable authoring sources, then export MOC3/motion3/exp3. Review real render sequences at equal scale. Current private sequences document the remaining limits; they do not claim improved art.

References: [Cubism material separation](https://docs.live2d.com/en/cubism-editor-manual/divide-the-material/), [deformers](https://docs.live2d.com/en/cubism-editor-manual/deformer/), [Open-LLM-VTuber](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber), [SAPI recognition](https://learn.microsoft.com/en-us/dotnet/api/system.speech.recognition.speechrecognitionengine).

Private models, SDK/Core, audio test inputs, chat and verification recordings remain outside public packages. The application/runtime/resource licenses are separate. Existing release and source-publication gates remain in effect.

## Use

Open the software assistant using the character or top bar. Its saved discussion section can search this character/project/model. Use complete commands such as `打开第八章`, `切换青岚书房主题`, `把正文字号调到18号`. Check the real execution receipt. For voice, select an installed system voice in the character settings and enable it, then opt in to reply reading in the assistant. Microphone recognition normally puts text in the input first; automatic sending is optional and low-confidence results still require review. Stop cancels the owned recognition/request/reading. Disabling reply reading mutes further automatic speech. No recognized speech bypasses Action permissions.
