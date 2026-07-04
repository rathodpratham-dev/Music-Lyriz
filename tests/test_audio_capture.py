from __future__ import annotations

from dataclasses import dataclass
import unittest

from audio.capture import AudioCapture
from audio.devices import list_system_audio_devices
from audio.levels import rms_level
from utils.settings import AudioSettings


@dataclass(slots=True)
class FakeDevice:
    name: str
    isloopback: bool


class FakeSoundcardModule:
    @staticmethod
    def default_speaker() -> FakeDevice:
        return FakeDevice("Speakers (Realtek Audio)", True)

    @staticmethod
    def all_microphones(include_loopback: bool = False) -> list[FakeDevice]:
        devices = [FakeDevice("Microphone (Realtek Audio)", False)]
        if include_loopback:
            devices.insert(0, FakeDevice("Speakers (Realtek Audio)", True))
        return devices


class AudioCaptureTest(unittest.TestCase):
    def test_default_device_uses_loopback_not_microphone(self) -> None:
        capture = AudioCapture(AudioSettings())

        device = capture._find_loopback_device(FakeSoundcardModule())

        self.assertTrue(device.isloopback)
        self.assertEqual(device.name, "Speakers (Realtek Audio)")

    def test_saved_loopback_device_name_matches_shorter_active_name(self) -> None:
        capture = AudioCapture(AudioSettings(device_name="Loopback Speakers (Realtek Audio)"))

        device = capture._find_loopback_device(FakeSoundcardModule())

        self.assertTrue(device.isloopback)
        self.assertEqual(device.name, "Speakers (Realtek Audio)")

    def test_audio_device_choices_include_default_and_loopbacks(self) -> None:
        choices = list_system_audio_devices(FakeSoundcardModule())

        self.assertIsNone(choices[0].device_name)
        self.assertTrue(choices[0].is_default)
        self.assertIn("Speakers (Realtek Audio)", choices[0].label)
        self.assertIn("Speakers (Realtek Audio)", [choice.device_name for choice in choices])

    def test_rms_level_handles_empty_audio(self) -> None:
        self.assertEqual(rms_level(None), 0.0)


if __name__ == "__main__":
    unittest.main()
