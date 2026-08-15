# Macro Alpha–style daily video factory

## Purpose and evidence boundary

This document turns the operating model described for the [Macro Alpha Chinese YouTube channel](https://www.youtube.com/@Macro_Alpha_cn) into a reproducible, human-governed workflow for zhihuiti.

The channel should be treated as a **creative reference, not a template to clone**. Channel-specific claims in this document are limited to the owner's stated operating model supplied with the request: a team of AI agents prepares videos every day and a human reviews and approves the content. Exact tools, prompts, revenue, and internal automation are not public evidence and must not be presented as facts.

Before matching the channel's presentation, manually sample at least 12 uploads (four recent, four median-performing, and four top-performing) and complete the scorecard below. This avoids confusing a plausible AI workflow with the creator's actual workflow.

## What to analyse in the channel

Record evidence at three levels rather than relying on general impressions.

| Level | Capture | Useful measurements |
|---|---|---|
| Packaging | title, thumbnail, publish time, description, playlist | title length and pattern, thumbnail word count, recurring visual grammar, posting cadence |
| Story | hook, thesis, sections, transitions, ending | seconds to thesis, section count, claims per minute, open loops, CTA placement |
| Production | narration, visuals, charts, captions, music | words per minute, shot duration, source labels, chart frequency, caption density |

For every sampled video, note timestamps at `0:00`, the first clear thesis, every section transition, the first cited source, and the CTA. Transcribe only enough to classify the structure; do not copy scripts, thumbnails, distinctive phrases, voice, or branding.

### Channel reverse-engineering scorecard

```yaml
video_id: ""
published_at: ""
duration_seconds: 0
views_at_capture: 0
packaging:
  title_pattern: ""
  thumbnail_words: 0
  thumbnail_subject: ""
  dominant_colors: []
story:
  hook_type: "question|surprise|consequence|forecast|other"
  thesis_timestamp: "00:00"
  section_timestamps: []
  claims: 0
  forecasts: 0
production:
  narration_wpm: 0
  median_visual_duration_seconds: 0
  charts: 0
  visible_source_labels: 0
  caption_style: ""
trust:
  primary_sources: 0
  secondary_sources: 0
  corrections_or_caveats: 0
notes: ""
```

After sampling, calculate medians—not just averages—and extract patterns present in at least 8 of 12 videos. Those recurring patterns become the house style. One-off details do not.

## The likely operating principle

A daily channel does not become reliable by asking one model to “make a video.” It becomes reliable by using a staged content supply chain with typed hand-offs, independent checks, and one accountable publisher. Agents should propose artifacts; deterministic software should render and validate them; the human should control claims, positioning, and publication.

```text
Sources → story candidates → editorial brief → evidence pack → outline
                                                        ↓
Publish ← human approval ← final QC ← rendered video ← script + scene plan
```

The human is the editor-in-chief. Automation may move an item between reversible draft states, but it must never cross the publication boundary on its own.

## Recommended agent team

| Agent | Responsibility | Required output | Must not do |
|---|---|---|---|
| Scout | Monitor approved feeds and identify material changes | source candidates with timestamps and URLs | infer a story from a headline alone |
| Pitch editor | Rank stories for audience relevance, novelty, and evidence | 3–5 scored pitches | select a story solely for predicted clicks |
| Researcher | Build a claim-level evidence pack | claims, excerpts, dates, source tiers, conflicts | cite search snippets or invent missing data |
| Macro analyst | Explain mechanism, scenarios, and counterarguments | thesis, causal chain, base/upside/downside cases | turn a scenario into certainty or advice |
| Scriptwriter | Convert the approved brief into original narration | script with claim IDs and timing | imitate the creator's distinctive wording |
| Visual director | Map narration to charts, maps, headlines, and licensed B-roll | scene manifest with provenance | request visuals without rights metadata |
| Fact-checker | Verify every checkable statement independently | pass/fail/needs-human report per claim | silently rewrite a failed claim |
| Compliance editor | Check financial, copyright, privacy, and platform risks | risk report and disclosure text | approve publication |
| Render worker | Generate narration, captions, charts, and edit timeline | deterministic render plus build log | alter claims to improve timing |
| QC agent | Check audiovisual and manifest invariants | machine-readable QC report | waive blocking errors |
| Publisher | Prepare title, description, chapters, and thumbnail variants | unlisted upload package | make the video public |
| Analyst | Capture post-publication results and corrections | retention and packaging report | reward unsupported sensationalism |

Use separate research and fact-check agents with isolated context. If the same agent writes and checks a claim, it tends to confirm its own framing.

## Daily state machine

Each episode is a durable record with explicit state transitions:

```text
DISCOVERED
  → PITCHED
  → BRIEF_APPROVED          # human gate 1: topic, thesis, risk budget
  → RESEARCHED
  → SCRIPTED
  → VERIFIED
  → RENDERED
  → QC_PASSED
  → RELEASE_APPROVED        # human gate 2: exact final artifact
  → UPLOADED_UNLISTED
  → PUBLISHED               # human action or short-lived signed approval
  → MEASURED
```

Any factual edit after `VERIFIED` returns the episode to `VERIFIED`. Any audio, caption, chart, title-card, or timeline change after `RELEASE_APPROVED` invalidates the approval hash. A failed check moves the item to `CHANGES_REQUESTED`, never forward with a warning.

### Suggested schedule

A sustainable daily process can run on overlapping tracks:

- **06:00–07:00:** ingest sources, deduplicate events, generate pitches.
- **07:00:** human chooses one brief and records framing/risk notes.
- **07:10–09:00:** parallel research, data retrieval, counter-thesis search.
- **09:00–10:30:** outline and script; claim ledger created automatically.
- **10:30–11:30:** independent fact-check and compliance review.
- **11:30–13:30:** scene generation, narration, captions, and rendering.
- **13:30–14:00:** automated QC and unlisted upload preparation.
- **14:00:** human watches at normal speed, checks flagged claims, and approves or rejects.
- **After release:** capture 1-hour, 24-hour, and 7-day metrics and corrections.

Keep at least two evergreen episodes in reserve. A daily deadline must not override a blocked source, market-moving correction, or failed render.

## Artifact contracts

Free-form prose between agents is difficult to audit. Each episode should contain versioned artifacts:

```text
episodes/2026-08-15-topic-slug/
  brief.json
  evidence.json
  claims.json
  script.md
  scenes.json
  assets.json
  compliance.json
  qc.json
  approval.json
  render/
    master.mp4
    captions.srt
    thumbnail-a.png
    thumbnail-b.png
```

A claim record should look like this:

```json
{
  "claim_id": "C014",
  "text": "The checkable statement as spoken",
  "type": "fact",
  "as_of": "2026-08-15T08:30:00Z",
  "sources": [
    {
      "url": "https://primary-source.example/report",
      "publisher": "Primary source owner",
      "published_at": "2026-08-15",
      "retrieved_at": "2026-08-15T08:31:00Z",
      "supports": "Exact table, paragraph, or dataset field",
      "tier": 1
    }
  ],
  "confidence": 0.92,
  "script_span": { "start": 812, "end": 901 },
  "verdict": "verified"
}
```

The renderer should reject a script containing a factual sentence without a claim ID. It should also reject missing asset licenses, expired market data, an unapproved synthetic-voice profile, or a scene whose on-screen number differs from its cited data field.

## Research and editorial rules

### Source hierarchy

1. **Tier 1:** central banks, statistical agencies, exchanges, company filings, legislation, and original datasets.
2. **Tier 2:** reputable reporting that identifies its evidence and date.
3. **Tier 3:** expert analysis used for interpretation, never as proof of an underlying number when the primary source exists.
4. **Discovery only:** social posts, aggregators, search snippets, and unsourced charts.

Market and macro claims require an `as_of` timestamp. Material claims should have either a Tier 1 source or two independent credible sources. Conflicts must be shown to the human rather than averaged away.

### Script structure to test

Do not assume this is the reference channel's formula until the sample confirms it. It is a strong starting structure for an original macro explainer:

1. **Cold open (0–20 s):** the changed fact and why it matters.
2. **Promise (20–35 s):** what the viewer will understand by the end.
3. **Context:** only the history required to understand the mechanism.
4. **Mechanism:** cause-and-effect chain supported by charts or documents.
5. **Countercase:** strongest evidence against the thesis.
6. **Scenarios:** base, upside, and downside with observable triggers.
7. **Takeaway:** summarize what to monitor; avoid personalized financial advice.

Label facts, interpretation, and scenarios in both the script and claim ledger. Prefer calibrated language such as “the evidence suggests” or “in the downside scenario” when certainty is not warranted.

## Human approval experience

The reviewer should not receive a chat transcript. Provide one compact review packet:

- 150-word brief and intended audience value;
- final video, script diff, and thumbnails;
- every high-risk claim with source preview and `as_of` time;
- fact-check failures, conflicts, low-confidence claims, and synthetic-media disclosures;
- copyright/license exceptions;
- title/thumbnail promise compared with what the script actually establishes;
- immutable hashes for the master video, captions, title, description, and thumbnail.

The only actions are `approve exact version`, `request changes`, `hold`, and `kill`. Approval records reviewer identity, timestamp, artifact hashes, disclosure version, and optional expiry. Upload credentials belong only to a narrow publisher service, not to research or rendering agents.

## Automated release gates

Block release when any of these are true:

- factual claim has no supporting citation or is marked disputed;
- live figure exceeds its freshness window;
- title/thumbnail asserts more certainty than the script;
- forecast is presented as a fact;
- chart axes, units, date range, or source label are missing;
- asset has no license/provenance record;
- quoted or third-party footage exceeds the editorial allowance;
- narration and captions disagree on a number, name, negation, or date;
- black frames, clipped audio, unsafe loudness, missing captions, or render duration mismatch occur;
- final artifact hashes differ from the approved hashes.

Use `ffprobe` for stream/duration checks, `ffmpeg` filters for silence/black-frame detection, a caption-to-script alignment check, and a schema validator for every JSON hand-off. LLM judgments can flag semantic risks but must not replace deterministic checks.

## Safety and originality

- Create a house style from audience needs and measured structural patterns; do not clone a living creator's voice, likeness, logo, thumbnail identity, or signature phrasing.
- Use a licensed voice or a voice whose owner gave explicit consent. Clearly disclose synthetic media when required by platform policy or applicable law.
- Do not use agent-generated investment recommendations as personalized advice. Separate evidence, interpretation, scenarios, and sponsorships.
- Store source snapshots or cryptographic hashes where licensing permits, so later corrections can reproduce what the reviewer saw.
- Maintain a visible corrections process. A corrected episode should link the correction and preserve an audit event rather than silently overwriting history.

## Metrics that improve the system without corrupting it

Track production and audience outcomes separately.

**Reliability:** unsupported-claim rate, corrections per episode, blocked-release count, stale-data failures, license exceptions, and reviewer overrides.

**Operations:** lead time, human review minutes, rerender count, cost per published minute, agent failure rate, and reserve depth.

**Audience:** click-through rate by packaging hypothesis, first-30-second retention, section-level retention, returning viewers, and satisfaction signals.

Never optimize agents directly for views. Use a constrained objective: maximize viewer value and retention only among episodes that pass evidence, originality, compliance, and approval gates. Otherwise agents learn sensational titles and overconfident forecasts.

## Implementation in zhihuiti

The repository already has orchestration, dependency-aware task execution, agent messaging, inspection, persistence, and human-governance concepts. Build the video factory as a product workflow on top of those primitives rather than embedding video-specific behavior in the core runtime.

Recommended milestones:

1. **Shadow mode (week 1):** sample the channel, finalize the house-style scorecard, and have agents produce briefs/evidence packs only. Publish nothing.
2. **Script mode (week 2):** generate claim-linked scripts and compare fact-check results with a human researcher.
3. **Render mode (weeks 3–4):** add scene manifests, licensed assets, TTS, captions, deterministic rendering, and automated QC; keep all uploads local.
4. **Unlisted pilot (week 5):** produce five full episodes, conduct human review, and record every override and correction.
5. **Limited release (week 6+):** publish no more than three episodes per week until unsupported claims, serious QC defects, and approval-hash mismatches are all zero for ten consecutive episodes.
6. **Daily operation:** enable daily cadence only when reserve depth is at least two and the reviewer can reliably finish the packet within the target review time.

### Definition of done for the first production episode

- all sampled style decisions are backed by the channel scorecard;
- every spoken factual claim resolves to a dated source record;
- every visual asset has provenance and reuse rights;
- independent fact-check and compliance reports pass;
- video, audio, captions, and metadata pass deterministic QC;
- human approves the exact final hashes;
- publisher uploads unlisted first and publication requires a separate human action;
- metrics and correction events are captured after release.

This design automates the repetitive production path while leaving editorial accountability where it belongs: with the human who approves the final claims and artifact.
