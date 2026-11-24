"""Windows WASAPI headphone/output level probe; no files or network audio."""

import argparse
import math
import sys
import time

import numpy as np
import pyaudiowpatch as pa


def list_devices(audio):
    wasapi = audio.get_host_api_info_by_type(pa.paWASAPI)
    devices = [
        d for d in audio.get_loopback_device_info_generator()
        if d["hostApi"] == wasapi["index"] and d["maxInputChannels"] > 0
    ]
    try:
        default_index = audio.get_default_wasapi_loopback()["index"]
    except (OSError, LookupError):
        default_index = None
    print("Available WASAPI output loopbacks:")
    for number, device in enumerate(devices, 1):
        marker = " [DEFAULT OUTPUT]" if device["index"] == default_index else ""
        print(f"  {number}. {device['name']}{marker}")
    if not devices:
        raise RuntimeError("No loopback devices found. Connect/enable an output device and rerun.")
    if default_index is None:
        print("Default output loopback unavailable; choose a numbered device.")
    return devices, default_index


def select_device(devices, default_index):
    while True:
        choice = input("Select device number (Enter = default output): ").strip()
        if not choice:
            for device in devices:
                if device["index"] == default_index:
                    return device
            print("No default loopback available. Enter a device number.")
        elif choice.isdecimal() and 1 <= int(choice) <= len(devices):
            return devices[int(choice) - 1]
        else:
            print(f"Enter a number from 1 to {len(devices)}.")


def measure_level(data):
    # Convert before squaring to avoid integer overflow. All channels contribute.
    samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
    return float(np.sqrt(np.mean(samples * samples))) if samples.size else 0.0


def monitor(audio, device):
    rate = int(device["defaultSampleRate"])
    channels = int(device["maxInputChannels"])
    # Callback replaces a single snapshot, keeping memory bounded. The main
    # thread stays interruptible even when WASAPI delivers no silent packets.
    latest = (0.0, 0.0, 0)
    callback_error = None

    def on_audio(data, frame_count, time_info, status):
        nonlocal latest, callback_error
        try:
            latest = (measure_level(data), time.monotonic(), status)
            return (None, pa.paContinue)
        except Exception as exc:
            callback_error = exc
            return (None, pa.paAbort)

    print(f"\nSelected: {device['name']}")
    print(f"Format: {rate} Hz, {channels} channel(s), 16-bit PCM")
    print("Listening to system output in memory only. No audio is saved or transmitted.")
    print("Play audio through this output. Press Ctrl+C to stop.")
    with audio.open(
        format=pa.paInt16, channels=channels, rate=rate, input=True,
        input_device_index=int(device["index"]), frames_per_buffer=1024,
        stream_callback=on_audio,
    ) as stream:
        while True:
            if callback_error is not None:
                raise RuntimeError(f"Audio processing failed: {callback_error}")
            if not stream.is_active():
                raise RuntimeError("Audio stream stopped. Check the output connection and rerun.")
            rms, timestamp, status = latest
            stale = time.monotonic() - timestamp > 1.0
            if stale:
                rms = 0.0
            db = 20 * math.log10(rms) if rms > 0 else -math.inf
            filled = round(max(0.0, min(1.0, (db + 60) / 60)) * 30)
            bar = "#" * filled + "-" * (30 - filled)
            note = "Waiting for audio" if stale else (f"Stream status: {status}" if status else "Audio active")
            print(f"\r[{bar}] RMS {rms * 100:6.2f}% | {db:6.1f} dBFS | {note:<26}", end="", flush=True)
            time.sleep(0.1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list-devices", action="store_true", help="Enumerate only; do not capture audio")
    args = parser.parse_args()
    if sys.platform != "win32":
        print("This probe requires Windows WASAPI.", file=sys.stderr)
        return 1
    try:
        with pa.PyAudio() as audio:
            devices, default_index = list_devices(audio)
            if not args.list_devices:
                monitor(audio, select_device(devices, default_index))
    except (KeyboardInterrupt, EOFError):
        print("\nStopped. Audio resources released.")
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"\nAudio error: {exc}", file=sys.stderr)
        print("Check Windows Sound output, reconnect headphones, then rerun the probe.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
