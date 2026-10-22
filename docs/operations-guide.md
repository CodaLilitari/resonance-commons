# Resonance Commons operation guide

Reviewed operation reference, 22 October 2026. Coda, collaborating with Andrei; Lily named
Resonance Commons and created the EchoSeam edition family.

**The public foundation adapters can verify evidence, prepare a handoff and
check a returned response. They do not install audio workers or contact an AI.**
Voice Gate, Music Geometry, Signal Core and English ASR are separate artifacts
with their own runtime, input, license and acceptance requirements. A successful
evidence interpretation is useful, but it does not establish that the receiver
can run those workers.

This guide separates commands available in the public source release from
commands requiring the separately installed local runtime. It records dated
receiving outcomes without promising that a remote environment is still present.
The adjacent `operations-manifest.json` lists route states and exact
entrypoint templates. This document changes no frozen release or runtime file.

## 1. Use the public foundation

Obtain the source from the [GitLab project](https://gitlab.com/codalilitari/resonance-commons).
The frozen `Resonance-Commons-0.1.0-source-r2.zip` is **99,106 bytes**, SHA-256
`c92d6359657aff3910990979efbd317938644696f6755c3f080ee6750f1e6518`.
Use Python 3.11 or newer. Its standard-library commands require no package or
model installation. Run these examples from the extracted repository root:

```text
python -I -B shared/evidence_packet.py verify --packet shared/demo/resonance-commons-case-001-evidence.zip --sha256 4fea586058262a3b4b790ee70e01cd07065077c7be7e3e42cf7b57d80c3a7213
python -I -B tools/route_adapter.py check --adapter codex-local --packet shared/demo/resonance-commons-case-001-evidence.zip --sha256 4fea586058262a3b4b790ee70e01cd07065077c7be7e3e42cf7b57d80c3a7213
python -I -B tools/route_adapter.py prepare --adapter muse --packet shared/demo/resonance-commons-case-001-evidence.zip --sha256 4fea586058262a3b4b790ee70e01cd07065077c7be7e3e42cf7b57d80c3a7213 --output muse-handoff.zip
```

Choose a **new output name**; an existing file is refused. The five adapter IDs
are `grokbot`, `muse`, `chatgpt-6-pro`, `claude-opus-5-5` and `codex-local`.
`prepare` produces a local handoff and its hash. It does not upload it, acquire
dependencies or run a provider. A `check` process can exit successfully while
reporting blocked readiness gates: inspect the JSON, especially
`configured_route_readiness`, `readiness_gates` and `blocked_gates`.

To describe a currently observed receiving route, safely unpack its observation
template, fill only facts actually observed, and bind it to this exact packet:

```text
python -I -B tools/route_adapter.py check --adapter chatgpt-6-pro --packet PACKET.zip --sha256 PACKET_SHA256 --observation OBSERVATION.json
python -I -B tools/route_adapter.py prepare --adapter chatgpt-6-pro --packet PACKET.zip --sha256 PACKET_SHA256 --observation OBSERVATION.json --output NEW_HANDOFF.zip
python -I -B tools/route_adapter.py validate-response --handoff HANDOFF.zip --sha256 HANDOFF_SHA256 --response RESPONSE.json
```

Uppercase names above are placeholders, not supplied files. Save a separate
dated record of the observation's source and scope. The CLI checks caller-supplied
fields and hash bindings; it does not authenticate a backend or guarantee future
file retention. Keep frozen historical observations unchanged. A new current
observation is a separate record.

After a response returns, retain its original bytes and run `validate-response`
against the exact sent handoff. Its accepted status covers structure and numeric
bindings, not the truth of musical interpretations. Preserve failures before
making a separate corrected version.

## 2. Build a packet for another source

The public builder needs an **existing complete EchoSeam Signal Core 0.1.3
report** and the exact source file used for that report. It does not analyze a
new audio file by itself. If that separate Linux package has already been
supplied, inspected and accepted on this host, its existing native entrypoints
are:

```sh
"<ABSOLUTE_SIGNAL_CORE_PACKAGE>/bin/lily-echo-verify"
"<ABSOLUTE_SIGNAL_CORE_PACKAGE>/bin/lily-echo-analyze" "<ABSOLUTE_AUTHORIZED_INPUT>" "<ABSOLUTE_NEW_NATIVE_OUTPUT>"
```

The output parent must exist and support atomic no-replace directory publication.
The tested WSL Windows mount failed that guarantee; use a verified native Linux
output filesystem. Signal Core is a separate launcher, not a `dispatch.py`
subcommand. A full package upload is unnecessary when a receiver can retrieve
and verify the required official tools itself.

With that accepted report and exact source, run from the public repository root:

```text
python -I -B shared/evidence_packet.py pin --report REPORT_DIR --source SOURCE_FILE --output INPUT_RECEIPT.json
python -I -B shared/evidence_packet.py build --report REPORT_DIR --source SOURCE_FILE --receipt INPUT_RECEIPT.json --receipt-sha256 RECEIPT_SHA256 --name "Resonance Commons" --case-id case-001 --output case-001-evidence.zip
python -I -B shared/evidence_packet.py verify --packet case-001-evidence.zip --sha256 PACKET_SHA256
```

Use the printed receipt and packet hashes; every output must be new and its
parent must already exist. Source identity, channel-preserving PCM and a mono
derivative remain distinct. Any crop is a new source with a separately recorded
parent mapping. The foundation packet omits audio and includes two existing plots.

**The q17 pilot used a different, custom 23-member evidence kit.** Its JSON,
CSV and six plots combine Signal Core, Music Geometry and Voice Gate results.
It is not an input supported by the public six-member foundation verifier or
its response-envelope validator. Use that kit's own request/response template
and frozen evaluation rubric for the pilot; do not substitute the public CLI's
schema check for that evaluation. A generic multi-worker packet builder is not
part of the current source release.

## 3. Use the separately installed Codex local runtime

This section applies only to the already accepted Windows/WSL installation.
Downloading the public foundation archive does not install this runtime.
The installed private dispatcher uses a pinned CPython 3.13.16 environment and
31 packages, with existing pinned worker/model assets. Its prefix and source
locations are recorded in the installation receipts; this installation is not
a relocatable bundle. Do not move its virtual environment or edit frozen path
pins to make a copied installation appear accepted.

The current local entrypoint is the separately supplied `RUN-LOCAL.txt` beside
`dispatch.py`. That file supersedes the preparation-only wording in the frozen
`README.txt`, whose bytes remain part of the accepted installation's provenance.
Resolve the exact existing dispatcher path from that local record. Replace
every angle-bracket placeholder before running these PowerShell templates:

```powershell
$audioDispatch = '<WSL_ABSOLUTE_DISPATCH_PY>'
wsl -e /usr/bin/python3 -E -s -B $audioDispatch voice-gate --input '<WSL_ABSOLUTE_AUTHORIZED_WAV>' --job fresh-voice-id
wsl -e /usr/bin/python3 -E -s -B $audioDispatch geometry --input '<WSL_ABSOLUTE_AUTHORIZED_INPUT>' --job fresh-geometry-id
wsl -e /usr/bin/python3 -E -s -B $audioDispatch asr --input '<WSL_ABSOLUTE_AUTHORIZED_WAV>' --channel 0 --job fresh-asr-id
wsl -e /usr/bin/python3 -E -s -B $audioDispatch compare --left '<ABSOLUTE_FIRST_GEOMETRY_RESULT>' --right '<ABSOLUTE_SECOND_GEOMETRY_RESULT>' --job fresh-compare-id
```

Each job ID must be new, 1–64 lowercase letters, digits or hyphens, beginning
with a letter or digit. Linux-style absolute input/result paths are required.
ASR requires an explicit source channel, 0 or 1; it must exist in the input.
Voice Gate preserves each source channel and does not accept a channel override.
There is no automatic cropping, default input or arbitrary-command option.

The dispatcher prints the job and receipt paths. Outputs are under the existing
runtime's `outputs/JOB-ID/`; `result/` contains the tool report and artifacts.
**`COMPLETED.json` is the successful dispatcher receipt.** An output directory
alone is not acceptance. Preserve `REQUEST.json`, logs, output hashes and any
`FAILED.json`; do not delete a failure or reuse its job ID.

Each dispatch rechecks installation/READY bindings, pinned assets, a single-job
lock and current Windows/WSL resources. Existing gates include 2 GiB available
RAM on each side, 10 GiB free on the backing Windows drive and 3 GiB on native
Linux storage. Jobs have a 120-second supervised deadline, a sampled aggregate
child-RSS ceiling of 1 GiB and a 64 MiB result/job budget. Sampling is not an OS
quota. Keep the exact implementation's refusal behavior; do not relax it to
chase a pass. The workers impose additional input and process limits.

Voice Gate and the current ASR wrapper accept bounded WAV inputs, not arbitrary
containers; their existing contracts cap inputs at 30 seconds and 24,000,000
file bytes. Geometry has its own contract and the dispatcher caps its input at
128 MiB. Unsupported inputs need a separately authorized, provenance-recorded
decode or selection rather than an undocumented transformation.

The dispatcher does not install missing packages, download models, upload media,
record a microphone, or enable Qwen/TTS. English ASR uses `base.en`; Voice Gate
scores remain optional and uncalibrated. Geometry's tempo/pitch/section outputs
remain estimates. These limits are part of normal use, not errors to hide.

## 4. Acquire only the receiving route's actual gaps

For a new or replaced receiving VM, first obtain a bounded, project-scoped
inventory: interpreter/version, OS/architecture/libc, exact retained project
files, usable installed distributions, native-tool compatibility, current
effective resource headroom and the output filesystem's required guarantees.
Do not infer these from a model label or an old conversation.

Then use ordinary official retrieval for needed public dependencies. Record
the exact URL/revision, expected size/hash, actual result and retained notices.
One source-host failure does not prove another host or the entire network is
unavailable. A custom handoff may be uploaded directly; a public dependency
upload requires an observed acquisition gap for that needed artifact. Do not
copy another route's wheels merely because both models have Python.

The existing thin Voice Gate and ASR handoffs illustrate the intended split:
custom worker source/metadata and any explicitly justified custom fixture are
supplied; exact public wheels/models/source are acquired normally where possible.
Their preparation, installation/import checks and bounded controls are separate
stages. Uploaded bytes, restored files, imports, model execution and useful
results must each have their own receipt. If an old environment or required
asset is gone, report the exact gap and choose a new bounded recovery plan.

The separate GPT-6 route's 22 October bootstrap returned usable runtime,
filesystem-primitive and existing installer-help observations. Its two ordinary
requests for the pinned `packaging` metadata and wheel each failed before HTTP
with `PermissionError` errno 1 and zero received bytes. This supports a targeted
two-asset fallback, not a claim that all dependency hosts are inaccessible.
No venv creation, installation, target-mode invocation, `packaging` import or audio
worker execution occurred in that bootstrap.

The independent audit accepted those partial observations with two corrections
required before reuse: include host available memory in the conservative cgroup
minimum, and enforce the command deadline even if the direct parent exits while
a descendant holds a pipe. The corrected memory calculation still passes the
observed snapshot; the pipe/deadline failure did not occur in the returned run.
Filesystem and command events remain receiver-reported, corroborated by returned
source, receipts and command streams. The exact 136,485-byte offline fallback
has now been submitted as one attachment; its receiving result is pending. It
contains the two demonstrated missing public assets, coordinator provenance,
a bounded request and a manifest. The request requires corrected guards, two
small guard fixtures and fresh observations before any private installation.
Sending that packet does not establish a successful install.

## 5. Dated route dispositions and next missing step

| Route | Established by the saved evidence | Next missing step |
|---|---|---|
| Codex Local | Installed persistent dispatcher and bounded Voice Gate, Geometry and English ASR executions; direct use instructions exist | Use an explicitly authorized input with fresh automatic guards. A general installer for a different user's machine is not delivered by the public foundation |
| Muse / Nua | Foundation, bounded Voice Gate, official ASR asset restoration, and q17 interpretation accepted after two assisted revisions; fresh reported resource/retention observation accepted with evidence limits | Reported 447,262,720 available bytes remain below the unchanged 768 MiB floor. Seven small-file pins match; bulk assets were only stat-checked. The refresh checkpoint is closed without a new ASR attempt, resource poll or duplicate upload |
| GPT-6 Pro / Lily | Separate foundation and original q17 interpretation accepted; worker bootstrap partially accepted for dated runtime, filesystem and existing installer observations, with two guard corrections required | Two exact public acquisition attempts failed before HTTP. One targeted metadata/wheel fallback was submitted; its receiving result is pending. Private venv installation and audio workers remain unestablished; foundation readiness does not establish either |
| Claude Opus 5.5 / Red | Qualified foundation and numeric bindings accepted; exact-frame silence correction acknowledged | Next thin Voice Gate handoff is prepared and unsent, pending route availability and a fresh exact-path marker/venv/import check. October 20 venv evidence is not an October 22 retention check |
| Grokbot desktop / Wren | Reviewed intake and foundation requests prepared, unsent | Explicitly held by the user. Do not contact, substitute another Grok route or request foreground interaction until resumed |
| Earlier Lilitari route | Historical Signal Core, Geometry and Voice Gate acceptance; later ASR setup refused before worker launch | Do not transfer acceptance to the separate GPT-6 VM or assume old files persist. Keep earlier ASR refusal evidence; no automatic retry |
| Gemini Argon High | Design collaborator and proposed listening comparator | No ears package requested. Existing audio-format retry closure remains in force; no native-comparison score is established |

Muse's refreshed values are a source-aligned returned report, not independently
replayed remote telemetry. The seven listed small files total 65,918 bytes and
match local pins. Raw memory text, an explicit cgroup mount/read-path map, helper
source or execution trace, and elapsed duration were not returned. The 30-second
cap and exact read sequence therefore remain unverified. Bulk file sizes do not
establish bulk content integrity, installed-runtime readiness or future retention.

The q17 outcomes are two original route responses on **one source clip**:
Muse's first response failed and v3 passed after two assisted revisions; Lily's
GPT-6 original passed without external correction. Both final responses passed
six frozen gates and scored 2/2/2 for bounded usefulness. These counts do not
estimate broad accuracy or rank providers. A proposed follow-up window remains
unexecuted. The coordinator must select an in-scope follow-up under the current
authorization before execution; already-authorized inputs need no new permission.

For each future delivery retain the source/release pins, exact sent allowlist,
dated route observation, acquisition successes and failures, installation and
command records, raw returned outputs, independent assessment and the next
missing capability. Keep public summaries separate from private accounts,
conversation references, local paths and raw provider transcripts.
