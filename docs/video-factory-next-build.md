# Video factory: next build plan

## Decision

The next build is **not another content agent**. It is a deterministic assembly worker that connects the files already produced on the Mac—script, shot manifest, narration, images, exposure correction, captions, and FFmpeg render—into one scheduler-safe command.

The current repository can discover episodes, generate/resume images, detect collisions and placeholders, and report image-level render readiness. It cannot yet reproduce the external `narrate.command`, `pipeline/exposure.py`, or the final render shown in the production workspace. Until those tools and representative manifests are brought into the repository, “daily automation” stops at image readiness.

## Milestone 1: import the real contracts

Bring sanitized copies of these artifacts into a fixture directory:

```text
tests/fixtures/video_episode/
  episode.json
  script.md
  shots.json
  audio/                 # one or two tiny fixture clips
  images/                # one or two tiny fixture images
```

Bring the executable pipeline into source control:

```text
scripts/narrate.command
zhihuiti/zhihuiti/video_exposure.py
zhihuiti/zhihuiti/video_render.py
```

Before changing formats, document the fields actually used by `narrate.command`, the exposure bands in `shots.json`, audio naming, shot timing, transitions, caption timing, music ducking, and render resolution. Tests must use the real field names. Do not invent a second episode schema.

**Acceptance criteria**

- `video doctor` understands `ep001_v4` and `ep002` without editing either manifest.
- A retired pilot is excluded based on `episode.json`, not its folder name.
- Expected audio and image filenames are derived exactly once from the manifest.
- The fixture can run offline and contains no credentials or copyrighted production media.

## Milestone 2: deterministic assembly worker

Add one idempotent command:

```bash
zhihuiti video assemble /path/to/ep001_v4
```

It should execute these stages:

```text
validate manifest
→ verify/generate narration
→ verify/generate images
→ normalize exposure into build/images/
→ generate captions
→ render into build/master.mp4
→ audiovisual QC
→ write build/build-report.json
```

Every derived file belongs under `build/`; source images and narration are immutable inputs. Each stage stores input hashes, tool version, arguments, outputs, duration, cost where known, and pass/fail state. A rerun skips a stage only when its input hash and output validation both match. Changing the script invalidates narration, captions, render, and QC; changing one image invalidates exposure for that image plus render and QC.

Never use shell-string execution. Invoke tools with argument arrays, capture stdout/stderr, apply timeouts, and write a stage report even on failure.

**Acceptance criteria**

- Running the same episode twice makes no paid calls and does not rewrite valid outputs.
- Interrupting at any stage can be resumed safely.
- Two workers cannot assemble the same episode simultaneously.
- A source file changing during assembly aborts the run.
- FFmpeg failure, missing font, clipped narration, missing caption, or duration mismatch returns a non-zero exit code.

## Milestone 3: measurable audiovisual QC

The QC worker must be deterministic first and semantic second.

Required checks:

- every expected image is readable and has the intended dimensions;
- measured exposure falls inside the shot's declared band after normalization;
- no dataless iCloud placeholder or conflict-copy filename is selected;
- narration segments exist, decode, and match the expected count;
- captions cover the narration timeline and contain every number/date/name from the approved script;
- output has one video and one audio stream, expected resolution/frame rate, and duration within tolerance;
- black-frame, freeze-frame, silence, clipping, and loudness thresholds pass;
- no source or build artifact changes after the report hashes are calculated.

Produce `qc.json` with individual measurements, thresholds, and evidence—not one model-generated boolean.

**Acceptance criteria**

- Tests deliberately inject a black frame, silent segment, wrong caption number, dark image, and missing audio file; each produces the correct blocking reason.
- The known-good fixture passes without network access.

## Milestone 4: unlisted delivery and human review

Only after assembly and QC are stable, add:

```bash
zhihuiti video upload-unlisted /path/to/episode
zhihuiti video approve-release EPISODE_ID --reviewer Ryan
zhihuiti video publish EPISODE_ID
```

Upload is always unlisted first. The review packet contains the rendered video, script diff, source/claim exceptions, QC measurements, thumbnail/title candidates, and immutable hashes. Approval binds the exact video, captions, thumbnail, title, and description. Publication rejects expired approval or any changed hash.

Send a notification when review is ready; do not automate approval. Upload and publish credentials belong to a narrow publisher process, not research, image, or render workers.

## Milestone 5: scheduled production

Replace the image-only launchd job with:

```bash
zhihuiti video assemble-all /path/to/episodes --notify
```

The scheduled command should:

1. acquire a root-level lease;
2. discover active episodes;
3. process the oldest approved brief first;
4. stop at the first human gate;
5. write a durable run report;
6. notify on success, blocker, or cost-budget exhaustion;
7. return non-zero when work expected to complete is blocked.

Add daily and per-episode spend ceilings before enabling paid narration or image calls. “Daily” must mean one scheduler invocation that safely resumes work, not a permanently open chat or two agents editing an iCloud folder.

## Milestone 6: editorial agent team

Only after deterministic production is dependable, automate the creative upstream:

```text
source scout → pitch ranker → human brief approval
→ researcher → counter-thesis researcher → scriptwriter
→ independent claim checker → scene planner → assembly worker
```

All agent hand-offs use versioned JSON artifacts and claim IDs. Research and fact-check agents use isolated context. Agents can request changes, but only the editor can approve the brief and exact release.

## Recommended order for the next session

1. Copy sanitized `ep001_v4/episode.json` and `shots.json` into test fixtures.
2. Add the real `narrate.command`, exposure script, and render command to the repository.
3. Write characterization tests before refactoring them.
4. Implement `video assemble` around those proven commands.
5. Make `ep001_v4` complete offline from fixture inputs.
6. Run the same pipeline against `ep002` to prove it is episode-independent.
7. Add QC failure fixtures.
8. Only then replace the 09:00 image-only launchd command.

The immediate deliverable is therefore: **one command that deterministically turns the existing `ep001_v4` artifact set into a QC-passed review video and can resume without duplicate spend.**
