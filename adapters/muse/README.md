# Muse adapter

This is a concrete configuration of the shared local capability-check and handoff
CLI. It does not contact a provider or automate the application.

Current snapshot: **bounded_runtime_probe_basis_corrected_for_observed_run**; access **available_in_observed_session**.
Native audio: **self_reported_unavailable**, with native-processing claims disabled.

WAV bytes and reported hashes matched the supplied fixture. A returned second-version result corrected the metric basis and its values were independently reproduced. This establishes only that bounded run. Runtime execution is distinct from native audio processing, which the route reported unavailable.

The observed half-sum/downmix calculation was independently reproduced and the returned second-version result corrected source-versus-derivative labels for that run. Reconfirm each source channel and metric basis for every new packet. Label 0.5/0.5 stereo averaging and its amplitude loss; never rename a downmix metric as source RMS.

Handoff: structured evidence files; optional exact-hash PCM16 WAV for an explicitly requested runtime probe.

Observed session reports Python 3.12.3 on Linux x86_64, NumPy 1.26.4, SciPy 1.11.4, FFmpeg 8.1.2 and matplotlib 3.6.3. Python wave byte processing and returned JSON artifacts were demonstrated. soundfile, librosa and onnxruntime were reported absent. Project source execution, model loading, wheel installation and PNG return remain untested. CPython 3.13-specific binary wheels are incompatible with this CPython 3.12 route. Reverify the active session before relying on these observations.

Run from the repository root:

```text
python -I -B tools/route_adapter.py check --adapter muse --packet PACKET.zip --sha256 PACKET_SHA256
python -I -B tools/route_adapter.py prepare --adapter muse --packet PACKET.zip --sha256 PACKET_SHA256 --output NEW_HANDOFF.zip
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
