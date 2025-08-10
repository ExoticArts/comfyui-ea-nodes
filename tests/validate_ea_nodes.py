# validate_ea_nodes.py
"""
Self-contained validator for comfyui-ea-nodes.
- Stubs `folder_paths` so we can import outside ComfyUI
- Imports nodes by file path (hyphen-safe)
- Verifies node registration
- Smoke-tests EA_SimpleFilenameCombine (prefix + delete variants)
- Smoke-tests EA_TrimImagesStartEnd when torch is available
"""

import os, sys, tempfile, shutil, pathlib
import importlib.util as iu

ROOT = pathlib.Path(__file__).parent.resolve()
NODES_DIR = ROOT / "nodes"


def load_module_by_path(mod_name: str, path: pathlib.Path):
    spec = iu.spec_from_file_location(mod_name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module {mod_name} from {path}")
    mod = iu.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


def ensure_folder_paths_stub(tmpdir: pathlib.Path):
    """Provide a minimal stub for ComfyUI's folder_paths module."""
    import types

    stub = types.ModuleType("folder_paths")

    def get_output_directory():
        return str(tmpdir)

    # Optional helpers not used here, but harmless to include
    stub.get_output_directory = get_output_directory
    stub.get_input_directory = lambda: str(tmpdir / "input")
    stub.get_temp_directory = lambda: str(tmpdir / "temp")
    stub.exists_annotated_filepath = lambda p: True
    stub.get_annotated_filepath = lambda p: str(p)

    sys.modules["folder_paths"] = stub


def main():
    tmpdir = pathlib.Path(tempfile.mkdtemp(prefix="ea_nodes_test_"))
    ok = True
    msgs = []

    try:
        # 1) stub folder_paths so imports don't blow up
        ensure_folder_paths_stub(tmpdir)

        # 2) import package-level __init__ (exposes mappings via nodes/__init__.py)
        pkg = load_module_by_path("ea_nodes_pkg", ROOT / "__init__.py")

        # 3) import nodes/__init__.py, which merges mappings
        nodes_mod = load_module_by_path("ea_nodes_pkg.nodes", NODES_DIR / "__init__.py")

        # 4) verify mappings exist and contain 2 nodes
        try:
            cls_map = nodes_mod.NODE_CLASS_MAPPINGS
            disp_map = nodes_mod.NODE_DISPLAY_NAME_MAPPINGS
            assert isinstance(cls_map, dict) and isinstance(disp_map, dict)
            expected_keys = {"EA_TrimImagesStartEnd", "EA_SimpleFilenameCombine"}
            assert expected_keys.issubset(set(cls_map.keys()))
            msgs.append(f"[OK] Node registration: {list(cls_map.keys())}")
        except Exception as e:
            ok = False
            msgs.append(f"[FAIL] Node registration: {e}")

        # 5) test EA_SimpleFilenameCombine (prefix + delete variants)
        try:
            NameNode = cls_map["EA_SimpleFilenameCombine"]()
            # Seed two fake old files to be deleted
            (tmpdir / "trim" / "6_belle").mkdir(parents=True, exist_ok=True)
            for n in (1, 2):
                (tmpdir / "trim" / "6_belle" / f"6_belle_00019_trim_{n:05}.mp4").write_text("x")

            prefix, fullstub = NameNode.build(
                subfolder="trim/6_belle",
                stem="6_belle_00019",
                suffix="_trim",
                ext="mp4",
                ensure_folder=True,
                delete_numbered_variants=True,
            )

            # Verify deletion happened
            leftovers = list((tmpdir / "trim" / "6_belle").glob("6_belle_00019_trim_*.mp4"))
            assert len(leftovers) == 0, f"Expected no numbered variants; found {leftovers}"
            # Verify prefix/stub
            assert prefix == "trim/6_belle/6_belle_00019_trim"
            assert fullstub == prefix
            msgs.append("[OK] EA_SimpleFilenameCombine: prefix + deletion")
        except Exception as e:
            ok = False
            msgs.append(f"[FAIL] EA_SimpleFilenameCombine: {e}")

        # 6) test EA_TrimImagesStartEnd if torch available
        try:
            import torch  # noqa: F401
        except Exception:
            msgs.append("[SKIP] EA_TrimImagesStartEnd (torch not available)")
        else:
            try:
                import torch
                import numpy as np

                TrimNode = cls_map["EA_TrimImagesStartEnd"]()
                # Build a tiny [N,H,W,C] tensor: N=5 frames
                frames = torch.from_numpy(
                    np.zeros((5, 8, 8, 3), dtype=np.float32)
                )
                trimmed, first, last = TrimNode.trim(frames, skip_first=1, skip_last=2)
                assert trimmed.shape[0] == 2, f"Expected 2 frames, got {trimmed.shape[0]}"
                assert first.shape[0] == 1 and last.shape[0] == 1
                msgs.append("[OK] EA_TrimImagesStartEnd: trim logic")
            except Exception as e:
                ok = False
                msgs.append(f"[FAIL] EA_TrimImagesStartEnd: {e}")

    finally:
        # Always clean temp dir
        shutil.rmtree(tmpdir, ignore_errors=True)

    print("\n".join(msgs))
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
