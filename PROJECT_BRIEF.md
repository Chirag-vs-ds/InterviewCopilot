# Build a Real-Time AI Interview Copilot for Windows

## 1. Project Overview

Act as a senior Python developer, AI engineer, Windows desktop application developer, and UI/UX designer.

I want you to **build a complete, functional Windows desktop application similar to Parakeet AI**, using Google Gemini as the AI engine.

The application should capture live system audio, detect spoken questions, convert them into text, generate short and accurate answers using Gemini, and display those answers in a lightweight desktop window.

**Primary use case:** Mock interviews, interview preparation, online meetings, technical assessments where AI assistance is permitted, and personal learning.

I want a working application, not just an explanation, architecture diagram, or sample code.

## 2. My System Configuration

- Operating system: Windows 11
- Laptop: ASUS Zenbook 14X OLED UM5401
- Processor: AMD Ryzen 7 5800HS
- RAM: 16 GB
- Primary programming language: Python
- AI provider: Google Gemini
- Preferred interface: Modern dark theme
- Preferred installation: Simple Windows executable
- Budget: Free or minimal cost

Optimize the application for smooth performance on my laptop.

## 3. Core Audio Capture Requirements

The most important feature is capturing audio directly from Windows.

The application must work when:

- Audio plays through laptop speakers.
- Wired headphones are connected.
- Bluetooth headphones are connected.
- USB headphones are connected.
- I am attending Zoom, Google Meet, or Microsoft Teams calls.
- The meeting application is minimized.
- My microphone is muted but another speaker is talking.

### Audio Capture Modes

Implement three selectable listening modes:

**Mode 1: System Audio Only**

Capture audio playing through the selected Windows output device using WASAPI Loopback or another reliable Windows-compatible method.

This should work even when audio is playing only through headphones.

**Mode 2: Microphone Only**

Capture audio from the selected microphone.

**Mode 3: System Audio + Microphone**

Capture both streams, ideally keeping their transcriptions and speaker sources separate.

### Additional Requirements

- Automatically detect available audio devices.
- Allow users to select the correct audio device.
- Handle headphones being connected or disconnected.
- Provide a simple audio level indicator.
- Include Start Listening, Pause, Resume, and Stop buttons.
- Handle Bluetooth audio-device switching.
- Display understandable errors if audio capture fails.
- Avoid routing audio through laptop speakers unnecessarily.
- Do not record or transmit meeting audio without the necessary consent.

## 4. Live Speech-to-Text

Convert incoming audio into readable English text.

Preferred technologies:

- Faster Whisper for local transcription.
- Alternatively, use a supported Google speech recognition API if it offers better latency.

Requirements:

- Automatically detect speech.
- Support English and Hindi-English mixed conversations.
- Ignore background noise where practical.
- Detect sentence boundaries.
- Handle pauses naturally.
- Display live transcription.
- Avoid sending duplicate questions to Gemini.
- Maintain a short conversation history.
- Use voice activity detection to reduce unnecessary processing.

The application should remain responsive while transcription is running.

## 5. Automatic Question Detection

Analyze transcribed speech and identify when a meaningful question is being asked.

Examples:

- "Tell me about yourself."
- "What is Python?"
- "Explain OOP concepts."
- "What is the difference between SQL and NoSQL?"
- "Explain your final-year project."
- "Why should we hire you?"
- "Write a Python program to reverse a string."

The detection system should:

1. Identify complete questions.
2. Recognize interview-style instructions that do not end with a question mark.
3. Avoid triggering on every sentence.
4. Combine incomplete speech fragments when appropriate.
5. Avoid generating duplicate answers.
6. Provide a manual **Generate Answer** button if automatic detection fails.

## 6. Google Gemini Integration

Use the official Google Gemini API and supported Python SDK.

Requirements:

- Securely accept a Gemini API key.
- Store credentials using Windows Credential Manager or an appropriate secure alternative.
- Never hardcode API keys.
- Use a currently supported Gemini model suitable for low-latency responses.
- Check current model availability and free-tier limits.
- Allow switching between supported Gemini models.
- Provide clear API error messages.
- Handle rate limits and temporary network failures.
- Include a connection test button.

Keep API usage economical.

### AI Answer Behavior

The AI should generate answers in simple, natural English.

Avoid overly complicated vocabulary.

Answers should sound like a fresher or final-year B.Tech student explaining a concept.

Provide response modes:

**Short Mode**
- 2–3 sentences.
- Direct and easy to understand.

**Normal Mode**
- 4–6 sentences.
- Include a small example where helpful.

**Detailed Mode**
- More complete explanation.
- Include technical details and examples.

**Coding Mode**
- Generate readable code.
- Explain the logic.
- Mention time complexity when relevant.

Answers must be accurate and should acknowledge uncertainty instead of inventing information.

## 7. Personalization Using Resume and Projects

Allow the user to upload:

- Resume in PDF or DOCX format.
- Project descriptions.
- Skills.
- Education details.
- Internship experience.
- Preferred job role.

Use the uploaded information when generating personalized answers.

For example:

**Question:** Tell me about yourself.

**Expected output:** A simple introduction based on my actual resume and educational background.

**Question:** Explain your project.

**Expected output:** Explain the relevant project using the uploaded project documentation.

Never invent work experience, technical skills, achievements, or project contributions.

Provide a profile editing screen.

## 8. Desktop UI Design

Create a beautiful, lightweight Windows desktop interface inspired by modern AI productivity tools.

Preferred design:

- Dark background.
- Rounded corners.
- Minimal layout.
- Smooth animations where practical.
- Modern typography.
- Blue and purple accents.
- Clear transcription and answer sections.

### Main Window

Display:

1. Application title.
2. Audio source selector.
3. Audio status.
4. Start/Pause/Stop controls.
5. Live transcription.
6. Detected question.
7. Gemini-generated answer.
8. Response mode selector.
9. Settings button.
10. Session history.

### Floating Answer Window

Implement an optional small floating window that:

- Can stay on top of other applications.
- Can be moved around the screen.
- Can be resized.
- Displays generated answers.
- Supports adjustable font size and opacity.
- Can be minimized to the system tray.
- Has a clear visible indication when audio capture is active.

Do not implement methods to secretly bypass screen sharing, recording, monitoring, or interviewer visibility. The floating interface should be intended for authorized assistance and practice.

## 9. Performance and Speed

Prioritize low latency.

Target the following where technically achievable:

- Quick audio capture startup.
- Partial transcription during speech.
- Fast question detection.
- Gemini response streaming.
- Display text as it is generated.
- Minimal CPU and RAM consumption.

Measure actual response times rather than assuming them.

Keep audio processing and API requests off the main UI thread.

Use asynchronous programming or worker threads where appropriate.

## 10. Additional Features

Implement the following if they do not compromise the core functionality:

### Interview History

Store:

- Date and time.
- Transcribed questions.
- Generated answers.
- Selected answer mode.

Use a local SQLite database.

### Keyboard Shortcuts

Provide configurable shortcuts for:

- Start/Pause listening.
- Generate answer.
- Clear current answer.
- Show/hide floating window.
- Switch response mode.

### Answer Controls

Add:

- Copy answer.
- Regenerate answer.
- Simplify answer.
- Expand answer.
- Explain with an example.
- Save answer.

### Privacy

- Show a clear active-listening indicator.
- Allow deletion of audio, transcripts, and history.
- Do not store raw audio by default.
- Explain what information is sent to Gemini.
- Provide a microphone/audio permission checklist.
- Do not enable recording automatically on application launch.

## 11. Recommended Technology Stack

Use the following unless a better technical choice is justified:

| Component | Technology |
|---|---|
| Language | Python 3.11+ |
| Desktop UI | PySide6 |
| System audio capture | Windows WASAPI Loopback |
| Microphone capture | sounddevice or suitable alternative |
| Speech-to-text | Faster Whisper |
| Voice activity detection | Silero VAD or WebRTC VAD |
| AI engine | Google Gemini API |
| API SDK | Official Google GenAI Python SDK |
| Local database | SQLite |
| Secure credentials | Windows Credential Manager/keyring |
| Application packaging | PyInstaller |
| Testing | pytest |

Verify compatibility with the current Windows environment and installed Python version.

## 12. Application Architecture

Organize the project into maintainable modules.

Suggested structure:

```text
InterviewCopilot/
│
├── main.py
├── requirements.txt
├── README.md
├── config/
│   └── settings.py
│
├── audio/
│   ├── device_manager.py
│   ├── system_capture.py
│   ├── microphone_capture.py
│   └── audio_processor.py
│
├── transcription/
│   ├── whisper_engine.py
│   └── question_detector.py
│
├── ai/
│   ├── gemini_client.py
│   ├── prompt_manager.py
│   └── resume_context.py
│
├── ui/
│   ├── main_window.py
│   ├── floating_window.py
│   ├── settings_window.py
│   └── styles.qss
│
├── storage/
│   └── database.py
│
├── tests/
│
├── assets/
│
└── build/
```

Adjust the structure if necessary.

## 13. Development Process

Complete the project in the following order.

### Phase 1: Environment Setup

1. Inspect the development environment.
2. Confirm operating system and dependencies.
3. Create the Python project.
4. Configure the virtual environment.
5. Install required libraries.
6. Verify Gemini API connectivity.

### Phase 2: Audio Capture

1. Implement system audio capture.
2. Implement microphone capture.
3. Add audio device selection.
4. Verify audio capture through wired and Bluetooth headphones.
5. Confirm audio can be captured without playing through speakers.

### Phase 3: Live Transcription

1. Integrate Faster Whisper.
2. Stream captured audio into the transcription engine.
3. Display transcription in real time.
4. Handle interruptions and silence.

### Phase 4: Gemini Integration

1. Implement question detection.
2. Send detected questions to Gemini.
3. Stream the AI response.
4. Implement short, normal, detailed, and coding modes.

### Phase 5: Desktop Interface

1. Build the main application window.
2. Add a floating answer window.
3. Connect controls to the working backend.
4. Add settings, status indicators, and keyboard shortcuts.

### Phase 6: Resume Integration

1. Implement resume upload.
2. Extract text from the uploaded file.
3. Build a user profile.
4. Generate personalized answers.

### Phase 7: Testing

Test the application using:

- Laptop speakers.
- Wired headphones.
- Bluetooth headphones.
- Google Meet audio.
- Zoom audio.
- Teams audio.
- Python interview questions.
- SQL interview questions.
- HR interview questions.
- Long questions.
- Short questions.
- Hindi-English mixed speech.
- Internet disconnection.
- Invalid API keys.
- Audio device switching.

Distinguish between tests actually executed and tests that require manual Windows hardware verification.

### Phase 8: Packaging

Build a Windows `.exe` installer or executable.

Ensure that:

- The application launches correctly.
- Dependencies are included.
- Audio capture works after packaging.
- No Python coding knowledge is needed for ordinary use.
- Configuration is persistent.
- API keys are not bundled into the executable.

## 14. Final Deliverables

I expect:

1. Complete, functional source code.
2. Modern desktop interface.
3. Working Windows system audio capture.
4. Headphone audio support.
5. Real-time transcription.
6. Google Gemini integration.
7. Live answer generation.
8. Resume and project personalization.
9. Floating answer window.
10. Configuration and history management.
11. Tests and error handling.
12. Windows executable or clear build instructions.
13. README with installation and usage steps.
14. Simple troubleshooting guide.

## 15. Important Instructions for ChatGPT Work

- **Do not stop after preparing a project plan.**
- Proceed to implementing the actual application.
- Do not generate only pseudocode.
- Create actual project files.
- Prioritize a working end-to-end MVP before advanced features.
- Test every component you can execute.
- Fix detected errors.
- Verify API and library documentation before implementation.
- Do not claim that an untested feature works.
- Do not claim a Windows executable has been tested unless it has actually run on Windows.
- If Windows hardware is unavailable, implement and test the components possible in your environment, then document exact Windows verification steps.
- Do not unnecessarily ask me questions.
- Make reasonable technical decisions independently.
- Explain installation in beginner-friendly English.
- Keep the application free or low-cost wherever possible.

## 16. Success Criteria

The project is successful when I can:

1. Launch the desktop application.
2. Connect headphones to my Windows laptop.
3. Play a spoken question from an authorized mock interview or test audio source.
4. Click Start Listening.
5. See the spoken question transcribed.
6. See the application automatically recognize the question.
7. Receive a short, accurate Gemini-generated answer.
8. Read the answer in the floating desktop window.
9. Switch between answer modes.
10. Stop listening instantly.

**Final instruction:** Build this as a real, usable Windows desktop application with reliable audio capture, fast AI answers, simple controls, and a professional interface. Focus on functionality first, then appearance and additional features.

