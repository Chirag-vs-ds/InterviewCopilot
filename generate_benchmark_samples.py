"""Inspect local Windows voices and synthesize public test questions if supported."""
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parent / "benchmark_samples"
root.mkdir(exist_ok=True)
script = r'''
Add-Type -AssemblyName System.Speech
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
$voices = $speaker.GetInstalledVoices()
$voices | ForEach-Object { Write-Output ($_.VoiceInfo.Name + ' | ' + $_.VoiceInfo.Culture.Name) }
$english = $voices | Where-Object { $_.VoiceInfo.Culture.Name -like 'en-*' } | Select-Object -First 1
$hindi = $voices | Where-Object { $_.VoiceInfo.Culture.Name -like 'hi-*' } | Select-Object -First 1
if ($english) {
    $speaker.SelectVoice($english.VoiceInfo.Name)
    $speaker.SetOutputToWaveFile((Join-Path $env:BENCHMARK_DIRECTORY 'english.wav'))
    $speaker.Speak('What is a dictionary in Python, and how does a hash table work?')
    $speaker.SetOutputToNull()
}
if ($hindi) {
    $speaker.SelectVoice($hindi.VoiceInfo.Name)
    $speaker.SetOutputToWaveFile((Join-Path $env:BENCHMARK_DIRECTORY 'hinglish.wav'))
    $speaker.Speak('Python mein dictionary kya hai, aur hash table kaise kaam karta hai?')
    $speaker.SetOutputToNull()
}
$speaker.Dispose()
'''
import os
env = dict(os.environ, BENCHMARK_DIRECTORY=str(root))
subprocess.run(["powershell", "-NoProfile", "-STA", "-Command", script], env=env, check=True)
