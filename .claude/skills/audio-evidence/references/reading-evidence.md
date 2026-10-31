# Reading the evidence

What each number and plot can show, where it misleads, and the targets people usually work to. Targets are context for Andrei's decisions, not rules: genre, intent and the release route decide.

## Bases

| Basis | What it is | Use it for |
|---|---|---|
| Source channels | The selected stream decoded by ffmpeg to 32-bit float, every channel kept, at the source rate (resampled to 48 kHz only above that) | Levels, peaks, DC, flat tops, silence, stereo |
| Mono derivative | The equal-weight mean of the channels | Spectral balance, plots. Never a source level |
| Feature signal | The mono derivative resampled to 22.05 kHz | Onsets, tempo, beats, pitch, chroma, sections |
| ffmpeg ebur128 | ffmpeg's EBU R128 / ITU-R BS.1770 meter on the selected stream | Loudness and true peak |

**Times** are seconds from the start of the decoded stream. For an MP3 or AAC file, ffmpeg removes the encoder delay, so time 0 is the first real sample, not the container's first byte.

**Lossy sources:** a decoded MP3, AAC or Ogg measures the decoder's output, not the master.

## Levels and peaks (measured)

- **`rms_dbfs`, `sample_peak_dbfs`, `crest_factor_db`:** whole-span averages and the largest sample. Crest factor (peak minus RMS) falls as a mix is limited harder:
  - dense modern masters sit around 7-10 dB;
  - dynamic acoustic material sits at 15-20 dB or more.
- **`near_full_scale_ratio` and `full_scale_runs_ge3`:** samples at or beyond ±0.999, and flat tops of three or more same-polarity samples.
  - Flat-top runs in a decoded file are strong evidence of clipping or brick-wall limiting somewhere in the chain.
  - They don't show where: in the master, in the encoder, or in Suno's renderer.
  - One or two short runs on a lossy file can be encoder overshoot.
- **`samples_over_full_scale`:** decoded float samples beyond ±1.0. Lossy decoders produce these when the master was close to 0 dBFS. They are real overs on playback through a fixed-point path.
- **`dc_offset_linear`:** anything beyond about 0.001 is worth a mention. It wastes headroom and can thump at edits.

## Loudness (measured, by ffmpeg)

- **Integrated LUFS:** the whole span, gated. Null means nothing rose above the absolute gate (silence).
- **Loudness range (LRA, LU):** the spread of short-term loudness, roughly:
  - 3-6 LU: heavily compressed pop and EDM;
  - 6-10 LU: most rock and pop;
  - 10-20 LU: film and classical.
- **True peak (dBTP):** ffmpeg's oversampled peak, overall and per channel.
- **Peak-to-loudness ratio (PLR):** true peak minus integrated loudness. Low PLR (under about 8 dB) means a dense, limited master.
- **Momentary (400 ms) and short-term (3 s) series:** in `data/loudness.csv` and `plots/loudness.png`. Use them for "where does it get louder" questions, not the integrated value.

**Streaming normalization**, as 2026 platform guides report it. Check the platform's own documentation before a release decision:

| Platform | Reference level | Direction |
|---|---|---|
| Spotify | -14 LUFS | Turns loud tracks down and quiet ones up |
| YouTube | -14 LUFS | Down only |
| Apple Music | -16 LUFS | Mostly down |
| Amazon Music, TIDAL | -14 LUFS | Up and down |
| Deezer | -15 LUFS | Up and down |

- **True peak:** -1 dBTP is the common ceiling. Spotify suggests -2 dBTP for masters louder than -14 LUFS, because encoding adds overshoot.
- **What normalization means for a master:** louder than the reference costs nothing in level after normalization, but keeps whatever dynamics were lost to reach it.

## Silence (measured)

- **The rule:** 20 ms frames where every channel is at or below -45 dBFS, merged, kept when they last at least 0.25 s.
- **Shorter dips** and quiet-but-not-silent passages can exist outside the listed intervals. Check `data/levels.csv` (100 ms RMS per channel) for those.
- **Leading and trailing silence** show up as intervals touching the span's edges.

## Edges (measured)

`edges` gives the loudest channel's RMS over the first and last 50 ms of the span.

- **Above about -30 dBFS at the end:** the file stops while sound is still playing. This is the classic hard end-of-file cut in a generated take: a word or chord ends in the middle.
- **On a deliberate span (`--end`):** the same flag only means the span boundary is inside the music.
- **A fade-out or natural decay** ends far below -30 dBFS.
- **What it settles:** a hard cut needs an extension or edit with real duration, not a lyric repair. The suno-production skill explains why that matters.

## Stereo (measured, two channels)

- **`correlation`:**
  - +1: identical channels (mono);
  - 0: unrelated channels;
  - -1: one channel is the other with its polarity inverted.
- **Windowed correlation:** the 0.2 s windows are what catch trouble. Sustained negative windows mean phase problems that will cancel in mono.
- **`mono_fold_down_change_db`:** the energy of (L+R)/2 against the mean channel energy.
  - 0 dB for mono content;
  - about -3 dB for uncorrelated content;
  - null when the channels cancel.

  Fold-down loss is not silence in the source, and a wide mix legitimately loses some level in mono.
- **`side_to_mid_db`:** width.
  - Below about -20 dB is nearly mono.
  - -10 to -6 dB is a wide mix.
  - Near 0 dB, side energy rivals the centre, which is unusual and worth checking.
- **`balance_left_minus_right_db`:** a few tenths of a dB is normal. Beyond about 1.5 dB, ask whether it's intended.

## Spectral balance (measured, mono derivative)

- **Band shares:** sub (20-60 Hz), bass (60-250), low-mid (250-2k), high-mid (2-6k), air (6-20k).
  - Shares depend on the genre and on the arrangement in the span.
  - Compare against the same song's previous render or a reference track Andrei names, never against an abstract ideal.
- **Centroid and 85% rolloff:** overall brightness. Use them for render-to-render comparisons.
- **`effective_bandwidth_hz`:** the highest frequency whose smoothed level stays within 50 dB of the 1-5 kHz median.
  - A sharp edge at about 16 kHz, or 19-20 kHz, is typical of lossy encoding at common bitrates. A 192 kbps MP3 test showed about 19 kHz.
  - Treat an edge as a hint about the file's history, not proof. Some masters are simply dark.
  - For Suno renders, compare the WAV and MP3 downloads before deciding which to master from.

## Estimates

Each estimate has a method and limits in the ledger. Say "estimated" when you use one.

- **Tempo:** autocorrelation of the onset envelope with a log-Gaussian prior around 120 BPM.
  - **Octave errors** (half or double) are the classic failure. Check the rhythm plot, and the stagecraft click preview when Andrei can listen.
  - **Windows:** `window_max_deviation_pct` over 20 s windows shows drift or tempo changes.
- **Beats:** a dynamic-programming tracker. Beat phase can lock to off-beats, such as a hi-hat pattern in a test, when they carry more transient energy than the kick. The tempo is still right when that happens.
- **Onsets:** mel spectral-flux peaks. Count and density, not note events.
- **Pitch (YIN):** predominant periodicity, 50-1000 Hz, in 20 ms frames.
  - **Solo lines:** on a solo voice or instrument, it tracks the melody well.
  - **Chords and dense mixes:** it often reports the common periodicity, the "missing fundamental". A C major triad reads as C2, two octaves below the chord.
  - Never present it as a melody transcription.
- **Chroma and key:** Krumhansl-Kessler profile correlation over the whole span.
  - Relative major and minor (C major / A minor) are often within a few hundredths of each other.
  - Modal, atonal or key-changing music fits poorly.
  - Report the runner-up and the margin. A margin under about 0.05 means "ambiguous".
- **Sections:** Foote novelty on beat-synchronous timbre. Boundaries are unlabelled.
  - Don't call them verse or chorus. That needs the lyrics, or Andrei.
  - Repeated material at regular spacing is a structural hint, not a label.

## Plots

| Plot | Read it for | Watch out |
|---|---|---|
| `waveform.png` | Envelope per channel (channels top to bottom), flat tops against the red full-scale lines, listed silence in grey | Min/max per pixel column hides short events. Probe a window for detail |
| `spectrogram.png` | Mono, log frequency with low frequencies at the bottom, 90 dB range. Bandwidth edges, hum lines, sibilance bands, arrangement changes | It's the mono derivative, so channel-only content is diluted |
| `loudness.png` | Momentary and short-term LUFS against the integrated line | Momentary jumps around by nature |
| `rhythm.png` | Onset strength with estimated beats; windowed tempo below | Beats can sit on off-beats |
| `pitch.png` | Voiced frames, coloured by confidence | Chords give missing-fundamental readings |
| `chroma.png` | Pitch-class energy over time and the key estimate | Percussion smears chroma |
| `sections.png` | Level with novelty and boundary estimates | Boundaries have no names |
| `stereo.png` | Windowed correlation, and side/mid energy below | Short negative spikes at transients are common |

## Things only a listener can judge

These include vocal performance and emotion, lyric intelligibility, whether an effect is musical or a glitch, genre fit, and "does it hit".

Give Andrei the evidence and the times to check (data tables have exact seconds), and say plainly that the judgement is his.

## Sources

The platform figures were checked on 27 October 2026 against [Fora Soft's 2026 platform table](https://www.forasoft.com/learn/audio-for-video/articles-audio/lufs-targets-per-platform-2026) and [Soundbridge's 2026 streaming guide](https://www.soundbridge.io/mastering-for-streaming-your-2026-platform-guide). Recheck them before advising on a release.
