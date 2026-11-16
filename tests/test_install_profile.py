"""Tests for the one-click profile installer, run against temp folders only"""

import json

import pytest

from src.install_profile import install_profile
from src.utils.bambu_studio import BambuStudioIntegration


class FakeBambu(BambuStudioIntegration):
    def __init__(self, root, running=False):
        self._running = running
        self.bambu_studio_path = root
        self.device_ids = self._find_device_ids()

    def is_bambu_studio_running(self):
        return self._running


@pytest.fixture
def profile(tmp_path):
    p = tmp_path / "src" / "My Profile.json"
    p.parent.mkdir()
    p.write_text(json.dumps({"name": "My Profile", "from": "User"}), encoding="utf-8")
    return p


@pytest.fixture
def bambu_root(tmp_path):
    root = tmp_path / "BambuStudio"
    (root / "user" / "123456" / "filament").mkdir(parents=True)
    return root


def test_installs_into_filament_folder(profile, bambu_root):
    out = []
    code = install_profile(profile, FakeBambu(bambu_root), ask=lambda q: "n", say=out.append)
    assert code == 0
    assert (bambu_root / "user" / "123456" / "filament" / "My Profile.json").exists()
    assert any("123456" in line for line in out)


def test_refuses_overwrite_unless_user_agrees(profile, bambu_root):
    target = bambu_root / "user" / "123456" / "filament" / "My Profile.json"
    target.write_text("ORIGINAL", encoding="utf-8")
    code = install_profile(profile, FakeBambu(bambu_root), ask=lambda q: "n", say=lambda m: None)
    assert code != 0
    assert target.read_text(encoding="utf-8") == "ORIGINAL"


def test_overwrites_when_user_says_yes(profile, bambu_root):
    target = bambu_root / "user" / "123456" / "filament" / "My Profile.json"
    target.write_text("ORIGINAL", encoding="utf-8")
    code = install_profile(profile, FakeBambu(bambu_root), ask=lambda q: "y", say=lambda m: None)
    assert code == 0
    assert json.loads(target.read_text(encoding="utf-8"))["name"] == "My Profile"


def test_refuses_when_bambu_studio_running(profile, bambu_root):
    out = []
    code = install_profile(profile, FakeBambu(bambu_root, running=True),
                           ask=lambda q: "y", say=out.append)
    assert code != 0
    assert any("close" in line.lower() for line in out)
    assert not (bambu_root / "user" / "123456" / "filament" / "My Profile.json").exists()


def test_reports_missing_bambu_folder(profile, tmp_path):
    out = []
    code = install_profile(profile, FakeBambu(tmp_path / "nope"), ask=lambda q: "y", say=out.append)
    assert code != 0
    assert out
