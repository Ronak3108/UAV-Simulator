"""
Weeks 9 and 11 — presets and export.

Run:  pytest -m "week09 or week11" -v
"""
import json
import numpy as np
import pytest

from simulator.state import SimConfig, DEFAULT
from simulator import presets, export, engine


# ==========================================================================
# Week 9 — presets
# ==========================================================================
@pytest.mark.week09
class TestPresets:

    def test_builtin_library_is_not_empty(self):
        assert len(presets.BUILTIN) >= 6

    def test_every_builtin_loads_and_is_valid(self):
        for name in presets.BUILTIN:
            cfg = presets.load_preset(name)
            assert isinstance(cfg, SimConfig)
            assert cfg.validate() == [], f"built-in {name!r} is not a valid config"

    def test_every_builtin_has_a_description(self):
        """The library doubles as documentation; a preset with no explanation
        teaches nothing."""
        for name, entry in presets.BUILTIN.items():
            assert entry.get("description", "").strip(), f"{name} has no description"

    def test_list_includes_builtins(self):
        listed = " ".join(presets.list_presets())
        for name in presets.BUILTIN:
            assert name in listed

    def test_save_and_load_round_trip(self, tmp_path, monkeypatch):
        monkeypatch.setattr(presets, "PRESET_DIR", tmp_path)
        cfg = DEFAULT.with_(formation="ring", n_uav=25, label="my test")
        presets.save_preset("mytest", cfg)
        assert presets.load_preset("mytest") == cfg

    def test_saved_file_is_readable_json(self, tmp_path, monkeypatch):
        monkeypatch.setattr(presets, "PRESET_DIR", tmp_path)
        presets.save_preset("readable", DEFAULT)
        path = next(tmp_path.glob("*.json"))
        json.loads(path.read_text())

    def test_will_not_overwrite_without_permission(self, tmp_path, monkeypatch):
        monkeypatch.setattr(presets, "PRESET_DIR", tmp_path)
        presets.save_preset("dup", DEFAULT)
        with pytest.raises(Exception):
            presets.save_preset("dup", DEFAULT.with_(n_uav=25))
        presets.save_preset("dup", DEFAULT.with_(n_uav=25), overwrite=True)
        assert presets.load_preset("dup").n_uav == 25

    def test_unsafe_names_do_not_escape_the_preset_directory(self, tmp_path, monkeypatch):
        """A user WILL type a name with a slash in it."""
        monkeypatch.setattr(presets, "PRESET_DIR", tmp_path)
        p = presets.save_preset("test 1/2: draft", DEFAULT)
        assert p.parent == tmp_path

    def test_builtins_cannot_be_deleted(self):
        assert presets.delete_preset(next(iter(presets.BUILTIN))) is False

    def test_user_presets_can_be_deleted(self, tmp_path, monkeypatch):
        monkeypatch.setattr(presets, "PRESET_DIR", tmp_path)
        presets.save_preset("temp", DEFAULT)
        assert presets.delete_preset("temp") is True
        assert not list(tmp_path.glob("temp*"))

    def test_missing_preset_raises_something_catchable(self):
        with pytest.raises(Exception):
            presets.load_preset("no-such-preset-anywhere")

    def test_old_preset_missing_a_field_still_loads(self, tmp_path, monkeypatch):
        """The compatibility promise: a file from week 5 opens in week 12."""
        monkeypatch.setattr(presets, "PRESET_DIR", tmp_path)
        (tmp_path / "ancient.json").write_text(
            json.dumps({"formation": "ring", "n_uav": 12})
        )
        cfg = presets.load_preset("ancient")
        assert cfg.n_uav == 12
        assert cfg.aperture == DEFAULT.aperture


# ==========================================================================
# Week 11 — export
# ==========================================================================
@pytest.mark.week11
class TestExport:

    @pytest.fixture(scope="class")
    def result(self):
        return engine.run(DEFAULT.with_(grid_points=101, label="exported"))

    def test_provenance_has_what_you_need_months_later(self):
        p = export.provenance(DEFAULT)
        assert "timestamp" in p
        assert "config" in p
        assert any("version" in k for k in p)

    def test_provenance_is_json_safe(self):
        json.dumps(export.provenance(DEFAULT))

    def test_single_result_to_csv(self, tmp_path, result):
        path = export.result_to_csv(result, tmp_path / "one.csv")
        assert path.exists()
        text = path.read_text()
        assert "res_x" in text and "pslr_y" in text

    def test_csv_gets_a_provenance_sidecar(self, tmp_path, result):
        """A results file without its parameters is worthless later."""
        path = export.result_to_csv(result, tmp_path / "one.csv")
        assert path.with_suffix(".json").exists()

    def test_many_results_to_one_csv(self, tmp_path):
        rs = [engine.run(DEFAULT.with_(grid_points=101, n_uav=n))
              for n in (4, 9, 16)]
        path = export.results_to_csv(rs, tmp_path / "many.csv")
        assert len(path.read_text().strip().splitlines()) == 4    # header + 3

    def test_figure_export_returns_png_bytes(self):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        ax.plot([0, 1], [0, 1])
        data = export.figure_to_png_bytes(fig)
        assert isinstance(data, bytes)
        assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
        plt.close(fig)

    def test_bundle_contains_everything(self, tmp_path, result):
        """
        The bundle contract. Name the files exactly — someone (or some script)
        will look for `psf.npy` by name six months from now, and "whatever the
        glob happened to return first" is not a contract.
        """
        folder = export.export_bundle(result, tmp_path)
        assert folder.is_dir()
        names = {p.name for p in folder.iterdir()}
        assert any(n.endswith(".csv") for n in names)
        assert any(n.endswith(".json") for n in names)
        assert "psf.npy" in names, f"expected psf.npy, got {sorted(names)}"

    def test_saved_psf_array_round_trips(self, tmp_path, result):
        """Reloading psf.npy must give back exactly the image that was shown."""
        folder = export.export_bundle(result, tmp_path)
        arr = np.load(folder / "psf.npy")
        assert arr.shape == result.image.shape
        np.testing.assert_allclose(arr, result.image)
