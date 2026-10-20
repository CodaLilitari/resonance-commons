# ChatGPT 6 Pro adapter

This is a concrete configuration of the shared local capability-check and handoff
CLI. It does not contact a provider or automate the application.

Current snapshot: **new_dedicated_conversation_not_created**; access **requested_model_temporarily_unavailable**.
Native audio: **not_verified**, with native-processing claims disabled.

The requested model was unavailable in the observed account session; no new target conversation or provider test was performed.

Create the required new dedicated conversation only when the exact requested model is usable. Another model or an existing unrelated conversation does not satisfy this adapter. An observed picker label is not backend attestation.

Handoff: a new dedicated project conversation with the exact requested model; attachment support must be checked there.

No runtime or media processing has been verified for the required new conversation.

Run from the repository root:

```text
python -I -B tools/route_adapter.py check --adapter chatgpt-6-pro --packet PACKET.zip --sha256 PACKET_SHA256
python -I -B tools/route_adapter.py prepare --adapter chatgpt-6-pro --packet PACKET.zip --sha256 PACKET_SHA256 --output NEW_HANDOFF.zip
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
