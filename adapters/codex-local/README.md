# Codex Local adapter

This is a concrete configuration of the shared local capability-check and handoff
CLI. It does not contact a provider or automate the application.

Current snapshot: **shared_packet_cli_verified**; access **local_cli_verified**.
Native audio: **not_claimed**, with native-processing claims disabled.

The shared producer CLI and five synthetic channel controls were verified locally. This establishes signal evidence handling, not subjective hearing or learned musical understanding.

Keep output state isolated and bounded. The local Qwen branch is blocked by available host memory; VoiceGate is a tested local candidate, not bundled here; Music Geometry later passed separate local and returned-target checks (see the [dated project update](../../status/2026-10-21.md)). None is enabled or treated as completed by this adapter. No dependency/model downloads or microphone access occur.

Handoff: local CLI packet verification and a machine-readable response; optional exact-hash WAV kept local.

The original local validation used Python 3.13.15 on Windows. Later Muse receipts support bounded execution of the supplied shared CLI on Linux; that receiver evidence does not establish every platform or adapter configuration.

Run from the repository root:

```text
python -I -B tools/route_adapter.py check --adapter codex-local --packet PACKET.zip --sha256 PACKET_SHA256
python -I -B tools/route_adapter.py prepare --adapter codex-local --packet PACKET.zip --sha256 PACKET_SHA256 --output NEW_HANDOFF.zip
```

A current observation can be supplied through `--observation OBSERVATION.json`.
Its explicit checks are in `profile.json`; the CLI verifies the observation's
packet/source bindings and type contract, not the provider's private backend.
An observation is caller testimony and cannot authenticate itself. A prepared
handoff never means uploaded, read, executed, or accepted by the provider.

For routes with an optional source WAV, `prepare --audio SOURCE.wav` accepts only
exact bytes matching the ledger's original-source hash, bounded PCM16 mono/stereo
and at most 30 seconds. It uses the opaque name `source.wav`; all other audio
paths and formats are refused. The complete handoff must fit the 10 MiB project
budget. Optional audio remains a distinct modality, without a native-hearing claim.

Returned measurements are checked against the request's exact metric IDs;
interpretations require evidence IDs and valid spans. Use `validate-response`
for structural/value-binding validation. It does not establish semantic truth.
