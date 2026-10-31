# Notice: audio-evidence

Original work by Red (Claude) for Andrei Kiralv, October 2026. MIT, under the plugin's licence.

## Code

- **`scripts/audio_evidence.py` and its tests are original.**
- **Rhythm and section estimates** (onset envelope, tempo autocorrelation with a log-Gaussian prior, dynamic-programming beat tracking, novelty boundaries) are adapted from the stagecraft skill's `song_map.py`, also Red's and MIT.
- **No code** from Resonance Commons, EchoSeam or any third-party audio library is included.

## Methods credited

- **Loudness and true peak:** EBU R128 and ITU-R BS.1770, measured by ffmpeg's `ebur128` filter (FFmpeg, LGPL/GPL, not bundled).
- **Pitch:** YIN, after A. de Cheveigné and H. Kawahara, "YIN, a fundamental frequency estimator for speech and music," JASA 111(4), 2002.
- **Key profiles:** C. L. Krumhansl and E. J. Kessler, 1982, as summarised in Krumhansl, *Cognitive Foundations of Musical Pitch*, 1990.
- **Beat tracking:** after D. P. W. Ellis, "Beat tracking by dynamic programming," JNMR 36(1), 2007.
- **Novelty:** after J. Foote, "Automatic audio segmentation using a measure of audio novelty," ICME 2000.

## Resonance Commons

- **The follow-up request shape** (`coda.audio-follow-up-request.v1`: one to three probes; `time-window`, `channel-view`, `higher-resolution-signal-measurement`; 30-second windows) follows the contract in Resonance Commons by Coda and Andrei, with Lily's EchoSeam (`gitlab.com/codalilitari/resonance-commons`).
- **Licence:** that project is source-available with reserved rights. Only the data format is shared, so requests can travel between routes; none of its code or text is copied here.

## Dependencies at run time

Python 3.10+, numpy, matplotlib (plots), ffmpeg and ffprobe. Claude's cloud workspace has them all. Nothing is bundled.
