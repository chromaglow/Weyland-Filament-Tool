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


def test_all_timemass_presets_install_into_temp_folder_and_cmd_lists_them(bambu_root):
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    res = root / "docs" / "research" / "timemass-plant-vitamin"
    names = ["TimePlast TimeMass Plant Vitamin", "TimePlast TimeMass Fire", "TimePlast TimeMass Detergent"]
    cmd = (root / "_for-ezra" / "01-import-timemass-profile.cmd").read_text(encoding="utf-8")
    for n in names:
        assert n in cmd
        code = install_profile(res / (n + ".json"), FakeBambu(bambu_root),
                               ask=lambda q: "n", say=lambda m: None)
        assert code == 0
        installed = bambu_root / "user" / "123456" / "filament" / (n + ".json")
        assert json.loads(installed.read_text(encoding="utf-8"))["name"] == n


def test_process_preset_installs_into_process_folder_only(tmp_path):
    root = tmp_path / "BambuStudio"
    (root / "user" / "123456" / "filament").mkdir(parents=True)
    (root / "user" / "123456" / "process").mkdir(parents=True)
    p = tmp_path / "src" / "0.30mm Test.json"
    p.parent.mkdir()
    p.write_text(json.dumps({"name": "0.30mm Test"}), encoding="utf-8")
    out = []
    code = install_profile(p, FakeBambu(root), ask=lambda q: "n", say=out.append, kind="process")
    assert code == 0
    assert (root / "user" / "123456" / "process" / "0.30mm Test.json").exists()
    assert not (root / "user" / "123456" / "filament" / "0.30mm Test.json").exists()


def test_process_install_asks_before_overwrite_and_refuses_while_running(tmp_path):
    root = tmp_path / "BambuStudio"
    (root / "user" / "123456" / "filament").mkdir(parents=True)
    target_dir = root / "user" / "123456" / "process"
    target_dir.mkdir(parents=True)
    p = tmp_path / "0.30mm Test.json"
    p.write_text("NEW", encoding="utf-8")
    (target_dir / p.name).write_text("OLD", encoding="utf-8")
    assert install_profile(p, FakeBambu(root), ask=lambda q: "n", say=lambda m: None, kind="process") != 0
    assert (target_dir / p.name).read_text(encoding="utf-8") == "OLD"
    assert install_profile(p, FakeBambu(root, running=True), ask=lambda q: "y",
                           say=lambda m: None, kind="process") != 0
    assert (target_dir / p.name).read_text(encoding="utf-8") == "OLD"
    assert install_profile(p, FakeBambu(root), ask=lambda q: "y", say=lambda m: None, kind="process") == 0
    assert (target_dir / p.name).read_text(encoding="utf-8") == "NEW"


def test_process_install_reports_missing_process_folder(tmp_path):
    root = tmp_path / "BambuStudio"
    (root / "user" / "123456" / "filament").mkdir(parents=True)
    p = tmp_path / "0.30mm Test.json"
    p.write_text("X", encoding="utf-8")
    out = []
    assert install_profile(p, FakeBambu(root), ask=lambda q: "y", say=out.append, kind="process") != 0
    assert any("process" in line.lower() for line in out)


def test_cli_process_flag_and_cmd_installs_process_preset():
    from pathlib import Path
    from src.install_profile import parse_args
    assert parse_args(["--process", "a.json"]) == ("process", "a.json")
    assert parse_args(["a.json"]) == ("filament", "a.json")
    cmd = (Path(__file__).resolve().parents[1] / "_for-ezra" / "01-import-timemass-profile.cmd"
           ).read_text(encoding="utf-8")
    assert "0.30mm TimeMass @BBL P1S 0.8 nozzle" in cmd and "--process" in cmd
