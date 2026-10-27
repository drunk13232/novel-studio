# AI Writing Quality Preview

Novel Studio 2.13 extends the existing Writer Context, Creative Director, selected-text assistance and ReviewCenter. No new agent, provider gateway, editor or scoring system is introduced.

## Daily use

1. Save the manuscript and inspect **This writing context**. Select the actual POV, story time, style and relevant references; explicitly approve the safe packet.
2. Open **AI Creative Director**. Quick mode uses the selected writer with compact source-bound methods, without an extra planning call. Director mode asks the selected commander for one scene. Deep mode retains the existing staged workflow.
3. Save the task brief, then choose **Inspect the actual writing brief**. It displays the scene boundary, actual method actions, input source titles and source hashes. It does not display hidden reasoning or give the model extra permissions.
4. Set the scene exit condition and outcomes left for later. These fields remain editable author plans, not story facts. An unresolved ending does not require the scene to stall.
5. Generated text is a candidate. Use the existing targeted review and guarded Diff before accepting any manuscript change. Pause, cancellation, retained-prefix intervention and manual takeover keep their existing behavior.

## Facts and creative freedom

The packet distinguishes established facts, present-scene creative freedom and consequential decisions that need the author. Dialogue, immediate behavior and incidental sensory details can be invented within the authorized scene. Major backstory, kinship, persistent identity, powers and state-changing outcomes cannot silently become established history.

Context selection prioritizes HARD constraints and POV knowledge, current intent/text, selected style, characters and near prose before distant references. Automatic near-field text is limited to the preceding two chapter numbers; sparse files are not silently promoted to adjacent context. Explicit pins and exclusions remain authoritative. A warning names omitted critical categories when the budget cannot fit them; inspect the actual sent list instead of assuming all references were read.

Selected style is evidence, not a generic instruction to write beautifully. Methods preserve author voice, ambiguity, functional repetition and varied narrative distance. Characters may change tactics under pressure; the system does not assign fixed slogans to each speaker.

Past-reference signals are narrow, low-certainty pointers into candidate sentences. They do not prove an invented fact, perform a semantic review, reject the candidate or change text. Use the existing evidence-bound reviewer and author judgment. A model can still miss a boundary or introduce unsupported details; prompt controls are not a proof of literary or factual correctness.

## Repeatable, isolated comparisons

The developer utility `scripts/writing_quality_experiment.py` copies only the public preview fixture into a new output folder. It never opens personal novels. Preparation is local:

```powershell
python scripts/writing_quality_experiment.py --output docs/ai-writing-quality/private-checks/my-run
```

`--run-ai --judge --resume` explicitly enables the existing Codex login for the original fixture prompts and the existing literary evaluator. No third-party paid API is selected automatically. Keep the output folder private. A separate run preserves failures and earlier versions.

Five bounded cases cover dialogue, suspense, value conflict, style and a roughly 3,000-Han-character continuous chapter. Generation order is counterbalanced; X/Y labels conceal the method from the grader. Both arms use the same approved source objects and author goal. Exact prompts, outputs, model receipts, timing, statistics, frozen rubric and verified quotations are retained. Human blind-review sheets are provided but are not automatically marked reviewed.

The same model may judge both candidates. That is an assistive opinion, not independent consensus or proof of improvement. Codex does not expose a strict ordinary-API output-token cap through this text session; target length, limits, prompt sizes and available usage must be reported honestly. Extra planning calls are separate from writer latency. Small samples and unequal realized lengths limit conclusions.

The method follows the [OpenAI evaluation guidance](https://developers.openai.com/api/docs/guides/evaluation-best-practices) on explicit criteria, representative examples, human calibration and order/verbosity bias. No hosted eval platform or additional dependency is required.

## Data and distribution

All manuscript changes still pass through the existing author-approved Diff and project scope. Canon, State, Knowledge and Final protection remain in force. Comparison records, author material, credentials, local logs and private character resources are excluded from public packages. Existing themes, automatic saving and offline writing remain available.
