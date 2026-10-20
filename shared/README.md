# Resonance Commons: Shared Evidence Packet Builder

Version 0.1.0, prepared by Coda in collaboration with Andrei. Lily selected the
shared project name Resonance Commons. EchoSeam remains Lily's edition family.
The packet display name remains configurable for separately configured routes.

This standard-library Python CLI turns an **existing Lilitari EchoSeam Signal
Core 0.1.3 analysis** into a small, route-neutral evidence ZIP. It does not run an
audio analyzer, Music Geometry, model, browser, network client or shell command.
The packet supports tool-mediated interpretation through numeric data, text and
two plots. It contains **no audio**, and it does not establish native hearing,
musical understanding, or the capabilities of any provider.

Python 3.11 or newer is required. The development validation used native Windows
Python 3.13.15. There are no dependency installs. The builder is operating-system
independent Python; atomic publication requires a filesystem supporting regular
file hard links and fails closed otherwise. Windows execution was checked; other
operating systems are not an executed portability claim from this release.

## Input and output

Provide the exact original source file and an existing complete EchoSeam 0.1.3
report directory. A local input receipt records the hash and length of the source
and every required report member. Because EchoSeam reports do not include a
producer-signed artifact manifest, this receipt is explicitly a **caller-pinned
snapshot**, not a producer signature. Pinning does not prove that the decoder
produced those PCM bytes from the original file.

The builder checks the report's original-source hash, schema/version, stream
index, PCM dimensions and per-channel measurements; independently recomputes
RMS, sample peaks, DC, near-rail ratio, zero crossings and silence intervals; and
checks the mono samples against the declared identity or 0.5/0.5 matrix within
half a PCM16 integer unit. It checks the timeline and waveform/spectrogram channel
mapping metadata. It does not independently run the EBU loudness algorithm or
recreate the plots; those are identified as producer-reported or producer-made.

The ZIP contains exactly:

- `manifest.json`: hashes and sizes of every other member; pin the complete ZIP's
  SHA-256 externally before transferring it.
- `ledger.json`: source identity, source/derivative measurements, transforms,
  decoded-stream time anchors, channel mappings, explicit unavailable branches,
  and evidence IDs.
- `instructions.txt`: fixed route-neutral interpretation instructions.
- `follow-up-contract.json`: the bounded proposal contract.
- `plots/waveform.png` and `plots/spectrogram.png`: the original existing PNGs.

The packet preserves the difference between original source bytes and the
decoded/resampled PCM16 measurement basis. Mono remains a separate derivative;
source-channel energy is never replaced by mono energy. The combined waveform's
channel indices increase **top to bottom**; the combined spectrogram's indices
increase **bottom to top**. A null gain is accompanied by its explicit zero-source
or zero-output status. PCM16 sample peaks and near-rail ratios are not measurements
of original-master clipping.

Times are seconds from the beginning of the decoded selected audio stream.
Parent-recording origin and original-container timecode remain null. A cropped
input is a new source; the tool does not invent its prior origin. Silence uses
20 ms all-channel RMS windows and the producer's minimum-duration filter. A gap
outside detected silence can contain shorter quiet intervals.

Tempo, beat tracking, pitch, harmony, instrument recognition, ASR, learned sound
events, semantic section labels and separation are explicitly unavailable. Empty
unattempted model results are not successful no-event detections.

## Commands

Use exact paths to existing files. Output parents must already exist; every output
must be new. Examples use placeholders, never a wildcard or a broad lab folder.

```text
python -I -B evidence_packet.py pin --report REPORT_DIR --source SOURCE_FILE --output INPUT_RECEIPT.json
python -I -B evidence_packet.py build --report REPORT_DIR --source SOURCE_FILE --receipt INPUT_RECEIPT.json --receipt-sha256 RECEIPT_SHA256 --name "Chosen Project Name" --case-id case-001 --output case-001-evidence.zip
python -I -B evidence_packet.py verify --packet case-001-evidence.zip --sha256 PACKET_SHA256
python -I -B evidence_packet.py validate-follow-up --packet case-001-evidence.zip --sha256 PACKET_SHA256 --request follow-up.json
```

`pin` also validates report consistency. Retain its printed hash and use it with
`build`; changing an input requires a new reviewed receipt and packet. The ZIP has
fixed member order/timestamps and is deterministic for the same inputs, name and
case ID. `verify` requires the externally supplied ZIP hash, checks every exact
member, and refuses unexpected members, duplicates, compression, symlinks and
member hash discrepancies. It never extracts an archive.

A follow-up request is only a proposal; validation never executes it:

```json
{
  "schema": "coda.audio-follow-up-request.v1",
  "source_sha256": "COPY_THE_EXACT_SOURCE_HASH_FROM_THE_LEDGER",
  "probes": [
    {
      "id": "probe-01",
      "operation": "channel-view",
      "start_seconds": 0,
      "end_seconds": 1,
      "channel_indices": [0]
    }
  ]
}
```

The allowed operations are `time-window`, `channel-view`, and
`higher-resolution-signal-measurement`. Each request has one to three unique
probes, finite forward time windows inside the decoded source extent, and valid
unique channel indices. Commands, URLs, filesystem paths, model instructions and
unknown fields are refused. A separate authorized producer must decide whether
and how to execute the request, with new evidence and provenance afterward.

## Bounds and safety contract

- Original source and report snapshot are each bounded to 64 MiB. Source PCM is
  mono/stereo, 8–192 kHz, at most 30 seconds. JSON is at most 256 KiB with at most
  32 nesting levels. Duplicate keys, NaN, Infinity and numeric overflow are refused.
- At most two PNGs enter the packet. Each is at most 2 MiB and eight million pixels.
  CRCs, bounded decompressed scanlines, ordinary RGB/RGBA form, and a restricted
  non-text chunk set are checked. Embedded text, EXIF and unrecognized metadata
  chunks are refused. No PNG editing or inference about its pixel content occurs.
- The complete ZIP is at most 10 MiB. The source filename, raw HTML, logs, probe
  metadata, original/derived audio and machine paths are omitted. Only explicit
  scalar fields and generated descriptions enter the ledger. Raw input HTML is
  hash-verified as bytes and never parsed or rendered.
- Case IDs have the opaque `case-NNN` form. Keep scoring references and descriptive
  audio labels outside provider packets. Source hashes are retained for provenance;
  they are not a promise of anonymity against an existing reference database.
- Static symlinks, Windows junctions/reparse points and multiply linked input files
  are refused. Outputs cannot reside inside the report directory. Unknown extra
  report-directory files are ignored and never read.
- Publication uses a temporary file in the output parent, flush/fsync, and an
  atomic **no-replace hard link**. Existing files/directories and a destination
  appearing at commit time are preserved. There is no replacing-rename fallback
  and no recursive deletion. Filesystems without this primitive fail explicitly.
- Parent directories must be trusted against concurrent malicious rename or
  reparse changes. Path checks are not an OS sandbox or proof against a hostile
  concurrent filesystem owner. A crash/SIGKILL can leave an owned temporary file;
  there is no claim of guaranteed cleanup after uncatchable termination.

No tool can turn matching hashes into a trusted producer signature. Pin receipts
and packet hashes through the intended trusted handoff. A forged report with a
new attacker-controlled receipt is not authenticated merely because its bytes
are self-consistent. Raw loudness values and plot fidelity retain their producer
provenance, even after the numerical consistency checks pass.

## Synthetic demo and checks

`demo/resonance-commons-case-001-evidence.zip` is a small example built from an existing independently
verified EchoSeam output for a public synthetic control. It is deliberately named
without its answer label. `demo/input-snapshot.json` pins its input bytes without
including local paths. `demo/SHA256SUMS.txt` supplies the transfer hashes. The demo
adds no native-audio, tempo, harmony or instrumentation capability.

Run the independent analytic/refusal tests:

```text
python -I -B tests/test_packet.py
```

The tests use a short, mathematically known alternating PCM fixture; they do not
run EchoSeam or import its code. They cover source and receipt tampering, wrong
PCM/matrix/channel/time mapping, status inflation, malformed JSON, unsafe archive
members, path and occupied-output refusal, a destination race, unsupported
publication primitives, privacy projection, deterministic output and follow-up
validation. The separate saved validation receipt records exercised real reports
and platform-specific skips. Nothing in this directory has been published.
