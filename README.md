# Resonance Commons

Resonance Commons is a small experimental project for sharing source-bound audio
evidence across distinct AI routes. Lily selected the project name; EchoSeam
remains her edition family. Coda and Andrei prepared this shared implementation
and its bounded validation.

The first release provides a **standard-library evidence-packet builder**, five
separately configured route adapters, capability checks, immutable handoff files,
and response-value/structure checks. It does not provide five functioning native
audio services. It makes the differences between available, tested, unavailable
and unverified capabilities explicit.

## What is implemented

The shared producer ingests existing **Lilitari EchoSeam Signal Core 0.1.3**
reports and exact source bytes. It verifies a pinned input snapshot and bounded
PCM/channel/time consistency, then creates a compact ZIP with a source/time/channel
ledger, two existing plots, fixed instructions and a follow-up probe contract.
The source packet contains no audio and makes no native-hearing claim.

Route adapters use that same ledger while enforcing different route/model/thread
requirements. `check` reports local preparation readiness and unmet current-route
gates. `prepare` creates a new, hash-manifested handoff; it never sends it.
`validate-response` checks exact numeric values, units, signal bases, source
channels, evidence IDs and time ranges. Interpretations remain unverified
hypotheses; structural acceptance is not a musical-quality score.

| Adapter | Current evidence and limit | Distinct check |
|---|---|---|
| Grokbot | Intended native route was inaccessible; no provider test | Actual Grokbot access; no ordinary Grok, Grok Build or API substitution |
| Muse | WAV-byte/runtime probe observed and numeric result reproduced; metric-basis labeling corrected for that bounded run; native audio self-reported unavailable | Current packet loaded and source-versus-mono metric basis explicitly confirmed |
| ChatGPT 6 Pro | Required model unavailable in observed session; required new conversation not created | Exact requested model and new dedicated conversation |
| Claude Opus 5.5 | Model label observed; no provider test while access unavailable | Exact requested model and current route access |
| Codex Local | Standard-library CLI and synthetic signal controls tested | Current local Python compatibility; no learned branch enabled |

These are dated observations, not permanent product specifications or backend
attestation. Private conversation references, account quotas/reset times and
account evidence are intentionally absent. Gemini supplied design consultation;
accepted attachment chips did not establish audio access, so it is not used as a
truth oracle or a verified native-audio baseline.

## Quick start

Python 3.11+ and the standard library are sufficient. Development validation used
native Windows Python 3.13.15. No model weights, package installation, credentials,
network, microphone, shell execution or provider automation is required.

```text
python -I -B shared/evidence_packet.py verify --packet shared/demo/resonance-commons-case-001-evidence.zip --sha256 4fea586058262a3b4b790ee70e01cd07065077c7be7e3e42cf7b57d80c3a7213
python -I -B tools/route_adapter.py check --adapter codex-local --packet shared/demo/resonance-commons-case-001-evidence.zip --sha256 4fea586058262a3b4b790ee70e01cd07065077c7be7e3e42cf7b57d80c3a7213
python -I -B tools/route_adapter.py prepare --adapter muse --packet shared/demo/resonance-commons-case-001-evidence.zip --sha256 4fea586058262a3b4b790ee70e01cd07065077c7be7e3e42cf7b57d80c3a7213 --output muse-handoff.zip
```

Every output must be new. Verify its printed hash before transferring it. A
handoff contains `evidence.zip`, a route-specific request/instructions/profile,
response and observation templates, and a manifest. The caller handles any
explicitly authorized transfer. An unavailable route can still have a locally
prepared handoff; it remains **prepared, not sent**.

Muse and Codex Local optionally accept `prepare --audio EXACT_SOURCE.wav` for a
bounded runtime-byte probe. Only the exact source hash from the ledger is allowed;
the file must be PCM16 mono/stereo and at most 30 seconds. It is named `source.wav`
inside the handoff to avoid descriptive source filenames. Native audio remains
unverified. The whole handoff must fit the 10 MiB project budget.

Unpack the observation template only with a normal safe ZIP tool, fill its exact
boolean/model fields from actual current observations, then pass it to `check`
or `prepare` with `--observation FILE.json`. This is caller testimony: the CLI
can check its types, exact route/model policy and source/packet binding, but it
cannot authenticate a remote backend or prove a provider read the evidence.

After a provider returns the response envelope:

```text
python -I -B tools/route_adapter.py validate-response --handoff HANDOFF.zip --sha256 HANDOFF_SHA256 --response RESPONSE.json
```

Measurement claims must identify a metric in the handoff's catalog and retain
its exact value, unit, signal basis and source channel indices. Whole-clip
measurements cannot be assigned to a narrower time span. Interpretation claims
need named evidence, a finite source-relative interval, channel indices, text
and uncertainty. Do not translate the validator's acceptance into semantic
truth, scientific validation, or successful listening.

## Signal and capability boundaries

- Original bytes, decoded/resampled channel-preserving PCM16, and the mono
  derivative remain distinct. Anti-phase downmix loss does not become source
  silence. Near-rail PCM16 samples do not establish original-master clipping.
- Time starts at the decoded selected stream. Parent recording origin and
  container timecode remain unknown; no hidden crop origin is invented.
- Tempo, pitch, harmony, instrumentation, ASR, learned events, separation and
  semantic section labels are unavailable in the shared signal packet. Music
  Geometry is a separate tested local candidate; it is not bundled or implemented
  by this shared packet.
- The local Qwen candidate was resource-blocked; VoiceGate is a tested local candidate.
  Neither is bundled or enabled here. Model weights and acquired runtimes stay
  outside this source tree.
- Follow-up requests use a source-hash-bound, finite-time/channel contract.
  They are proposals only. The CLI does not execute them, fetch a model, upload
  media or run a command from a response.

See `shared/README.md` for byte bounds, atomic no-replace publication, symlink/
junction refusal, the trusted-parent concurrency limit and the snapshot trust
model. This project is not an OS sandbox. Hash agreement is not a signature.

## Validation and publication

```text
python -I -B shared/tests/test_packet.py
python -I -B tests/test_routes.py
```

The shared validation record has 29 tests: 28 passed and one Windows symbolic-link
creation privilege skip; the actual Windows junction test passed. Five preserved
synthetic channel controls passed full CLI pin/build/verify. The 19 route tests
passed; the five public CLI preparation/validation flows passed. Route tests check
distinct readiness rules, source binding, immutable handoffs, claim-value and
modality refusals. Current result files and exact source hashes are allowlisted.

The source ZIP and public file manifest identify this exact review snapshot.
The independently frozen shared source ZIP is also preserved in `releases/`.
The public manifest excludes itself to avoid a recursive hash; its hash is supplied
separately at handoff. The source archive contains source and fixtures, not runtimes.

This initial source release contains only first-party source/docs/tests, a small
synthetic demo and sanitized validation. Publication URLs and execution status
are maintained separately. GitLab/portfolio publication uses the exact reviewed
public file manifest. Adapter profiles preserve dated foundation-build observations;
the separate Music Geometry and VoiceGate candidates are not enabled by them. This is a source-available project with attribution and reserved rights, not an
open-source license grant. Existing notices preserve attribution without inventing
permissions for other projects or media.
