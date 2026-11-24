# Interview Copilot desktop MVP

Windows 11 / Python 3.11.

## Setup

Clone this repository, open PowerShell in its folder, and create a local environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The virtual environment and downloaded models are excluded from Git.

## Launch

From this folder in PowerShell (no activation needed):

```powershell
.\.venv\Scripts\python.exe main.py
```

1. Wait for **Whisper base ready**. Multilingual base loads once per process on CPU
   with int8 and four CPU threads. First run downloads into `.models`; later runs
   use the cache. Start retries a failed load.
2. Open **Settings**, enter your Gemini API key, then **Load available models**.
   Select a text-generation model, **Test Connection**, then **Save**. The test
   makes a small generation request. Listing does not guarantee generation quota.
3. Select your headphone output and **Start**. Play spoken test audio through it.
   The green LISTENING indicator confirms capture is open.
4. Pause about a second after your question. The finalized transcript appears;
   recognized questions/instructions automatically request a streamed answer.
5. Edit any detected question or type one, then use **Generate Answer** manually.
6. **Stop** closes capture and discards pending audio and late results.

Without a Gemini key, local capture/transcription still work. Personal answers
use confirmed profile facts when available, with placeholders for missing facts.

## Resume and profile

Open **Profile** to import a text-based PDF or DOCX, or paste text into the source
box for scanned PDFs. Extraction happens locally in a background worker. No OCR
or resume upload to Gemini occurs. DOCX paragraphs/tables are supported; complex
layouts/text boxes and mixed scanned PDF pages may need manual pasted corrections.

Select relevant text in the source preview and use **Copy selected source text to
field**, or type into the education, skills, internships and preferred-role fields.
Under **Projects**, add each project name, what it does, and what you personally
built. Review these fields, check the confirmation box, and click **Save Confirmed
Profile**. Editing a field clears confirmation. Cancel/close discards unsaved edits.
Imported source text and file paths are never saved with the profile.

Only the confirmed structured facts are stored, in plain local JSON at
`local_data/profile.json` (excluded from Git). **Clear Profile** deletes that saved
file and clears the current app's profile. Save/Clear also cancels pending answers
and clears the shared answer view so queued requests cannot reuse old facts;
already sent requests cannot be retracted. Source resume files are unchanged.

Personal-question matching is conservative and local: education questions use
education only; internship questions use internships; project questions use the
named project, or the first project for a generic 'your project' question. General
technical questions receive no profile data. Self-introduction uses education,
skills, internships and preferred role. Unknown or absent facts use explicit
bracketed placeholders, with instructions never to invent experience/contributions.
Manual and automatic questions share this same request builder and answer stream.
Unrecognized personal phrasing can be reworded in the editable question field.

Profile tests cover actual PDF/DOCX fixtures, scanned/empty fallback, confirmation,
save/reload/clear, unsaved import previews, missing facts, selective context and
manual/automatic SDK requests with shared floating-window updates. No real resume
or personal facts were sent to Gemini during these tests; live wording quality
still needs verification with your own confirmed profile.

Click **Floating Answer** to open a movable, resizable, always-on-top answer
window. It shares the main answer text and live listening indicator. Its
**Stop Listening** button uses the same Stop action as the main window.
Closing it hides it; click Floating Answer again to reopen it with the current
answer. Closing the main app closes both windows. A visible 24-pixel QSizeGrip
at the bottom right resizes the floating window. Actual Windows mouse dragging
was verified: 560x420 -> 572x432 -> the 320x200 minimum client size. Shared
streaming, Stop, reopen and always-on-top flags remain covered by tests.

## Latency measurements

The launch terminal prints content-free JSON timing records using monotonic
timestamps. Records contain only a fixed stage name, numeric ID and milliseconds:

- `speech_to_finalize`: estimated timestamp of the last captured VAD-positive
  frame to utterance finalization. Callback timestamps and buffered frame duration
  locate the frame; this includes endpointing/buffering, not acoustic ground truth.
- `whisper`: transcription call through consumption of its segment generator.
- `answer_queue`: enqueue to request worker start (includes thread scheduling).
- `gemini_to_visible`: request worker start, including client setup, to completion
  of the first Qt paint with non-whitespace answer text in either answer window.
  This includes the UI polling delay. It measures Qt painting, not monitor/compositor
  presentation. If neither window is visible, it waits for a visible paint.

Audio metrics use the capture-session ID; answer metrics use the request ID.
Keys, prompts, transcripts and answers are never included in these timing records.
Failed/empty requests do not produce a first-visible-text measurement.

Measured on this laptop (synthetic English question, same audio, three alternating
warm runs per beam, multilingual base CPU int8):

| Experiment | Baseline | Candidate | Decision |
|---|---:|---:|---|
| Whisper beam 3 vs 1, median | 1469 ms | 1485 ms | Keep beam 3 |
| Technical terms retained | 3/3 every run | 3/3 every run | Both passed this sample only |
| Paced silence simulation, 900 vs 690 ms | 922 ms | 687 ms | Keep 900 ms |
| Segments with 750 ms internal hesitation | 1 | 2 | Shorter pause split the question |

Both thresholds produced one utterance for the synthetic English recording.
The terms checked were Python, dictionary and hash table. Windows had only
English voices, and no Hindi-English recording was available: mixed-language
accuracy/speed comparison is **not completed**. No beam/pause default was changed.
There is therefore no claimed before/after end-to-end speedup.

Two live public-prompt Gemini requests had 0 ms queue wait at clock resolution.
One produced no visible text (no latency available); the other measured 3641 ms
to first Qt paint. Gemini exceeded the local Whisper time on that successful
request, but this limited sample does not establish consistent dominance.

Reproduce or supply real recordings (the benchmark logs timings and numeric term
recall, never recognized text):

```powershell
.\.venv\Scripts\python.exe generate_benchmark_samples.py
.\.venv\Scripts\python.exe benchmark_latency.py --english path\english.wav --hinglish path\hinglish.wav
.\.venv\Scripts\python.exe benchmark_gemini.py
```

Use the same question about Python dictionaries and hash tables in both languages
for the fixed term check, and review recognition quality manually before tuning.
`benchmark_results.json` contains the measured local results. Generated test WAVs
are synthetic speech only, not saved user audio. The Gemini benchmark uses the
saved key/model for two public questions and temporarily opens a Qt window.

## Behavior and privacy

- Reuses the working probe helpers and native-rate int16 WASAPI callback approach.
  Downmixes all channels to mono, then uses streaming soxr resampling to 16 kHz.
- WebRTC speech detection: 30 ms frames, 300 ms pre-roll, 900 ms pause, 25-second
  maximum utterance. No-packet silence also finalizes speech.
- Transcripts appear after utterances, not as partial live words. Automatic language
  detection supports multilingual input; mixed Hindi-English accuracy needs testing.
- Capture, resampling/VAD, transcription, model loading, credentials and API calls
  run outside the UI thread. Bounded queues report overload.
- Question detection uses heuristics. Normalized duplicates are sent automatically
  once per listening session. Manual Generate Answer permits retries.
- Stop invalidates session/request IDs. In-progress native transcription can finish
  in the background, with results ignored. Gemini requests already sent cannot be
  retracted; late chunks are ignored. Network requests have a 30-second timeout.
- Raw audio stays in RAM and is never saved or uploaded. Only finalized or manually
  edited questions and a fixed answer instruction go to Gemini. No transcript
  history is persisted. The key is saved using keyring's Windows Credential Manager
  backend; only the model name goes into Windows application settings.
- Audio routing is unchanged. No microphone capture is included in this MVP.

## Verification

Executed here: dependency/import checks; 10 automated tests covering question
examples, deduplication, pause segmentation, 44.1/48/96 kHz resampling, mocked
streaming, late-result suppression and capture cleanup; real multilingual base
CPU int8 model loading and silent transcription; offscreen Qt startup, enumeration
and shutdown; short real headphone stream open/close.

Still manual: spoken English/Hindi-English accuracy and latency, end-to-end
headphone playback, Stop during speech/streaming, reconnect/Bluetooth switching,
and Gemini model listing, credential save/reload, connection and actual streaming
with your API key. Free quota/model access were not verified.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe smoke_check.py --capture --model
.\.venv\Scripts\python.exe check_model.py
```

After changing devices: Stop, Refresh outputs, select output, Start. For a zero
meter, check Windows/app routing and mute settings. Raise playback volume for
quiet speech. Base may misrecognize accents, mixed languages and noisy audio.
For Gemini errors, test another available text model or retry later. Requests
are not automatically retried to avoid duplicate sends.

Settings keeps separate results for **Load available models** and **Test Connection**.
API failures show the actual HTTP status and a sanitized SDK message, with keys
and URLs removed. Connection failures without a Gemini response explicitly show
that no HTTP status is available. Test Connection sends only the dropdown's selected
model and `Reply with OK.`; it does not apply answer-generation settings or token
limits. The dropdown includes API-returned models supporting `generateContent`.

Reinstall dependencies or run the original terminal probe:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe audio_probe.py
```

References: [PyAudioWPatch](https://github.com/s0d3s/PyAudioWPatch),
[Faster Whisper](https://github.com/SYSTRAN/faster-whisper),
[Google Gen AI SDK](https://googleapis.github.io/python-genai/).
