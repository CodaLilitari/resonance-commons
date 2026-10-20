# Grokbot adapter

This is a concrete configuration of the shared local capability-check and handoff
CLI. It does not contact a provider or automate the application.

Current snapshot: **not_sent**; access **unavailable_to_current_operator**.
Native audio: **not_verified**, with native-processing claims disabled.

The intended native application could not be accessed through the available control surface. No provider response was obtained.

Use the actual Grokbot route. Ordinary Grok chat, Grok Build and an xAI API endpoint are separate routes and cannot silently substitute. Return unavailable if the actual application cannot be operated.

Handoff: text-first evidence; add plots only after the actual application attachment surface is verified.

No executable runtime has been verified for this route.

Run from the repository root:

```text
python -I -B tools/route_adapter.py check --adapter grokbot --packet PACKET.zip --sha256 PACKET_SHA256
python -I -B tools/route_adapter.py prepare --adapter grokbot --packet PACKET.zip --sha256 PACKET_SHA256 --output NEW_HANDOFF.zip
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
