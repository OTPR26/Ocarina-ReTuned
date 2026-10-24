"""Apply the experimental backend to a private Switch engine and SDL source tree.

No SDK install or remote operation is performed. The existing OpenGL build is
unaffected. Sources must match the locally validated engine and SDL 2.28.5.
"""
from pathlib import Path
import argparse
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent


def apply_patch(tree: Path, patch: Path):
    def run(*flags):
        return subprocess.run(
            ["patch", "-p1", "--batch", *flags, "-i", str(patch)],
            cwd=tree, text=True, capture_output=True,
        )
    check = run("--dry-run", "--forward")
    if check.returncode:
        if run("--dry-run", "--reverse").returncode == 0:
            return
        raise RuntimeError("Source does not match the deko patch:\n" + check.stdout + check.stderr)
    result = run("--forward")
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)


def apply(engine: Path, sdl: Path, sdk: Path):
    engine, sdl, sdk = engine.resolve(), sdl.resolve(), sdk.resolve()
    # Fail on mismatched patches before copying backend files.
    apply_patch(sdl, ROOT / "sdl-external-display.patch")
    apply_patch(sdl, ROOT / "sdl-audio-progress.patch")
    apply_patch(engine, ROOT / "engine.patch")
    shutil.copy2(sdk / "portlibs/switch/include/SDL2/SDL_config.h", sdl / "include/SDL_config.h")
    dest = engine / "runtime/three_ds_recomp/src/fast/backends/retuned_deko"
    dest.mkdir(parents=True, exist_ok=True)
    for source in ROOT.iterdir():
        if source.suffix in (".h", ".cpp"):
            shutil.copy2(source, dest / source.name)
    shutil.copy2(ROOT.parent / "shader_compat.h", dest / "shader_compat.h")
    if __package__:
        from .settings import apply as apply_settings
    else:
        from settings import apply as apply_settings
    apply_settings(engine)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", type=Path, required=True)
    parser.add_argument("--sdl", type=Path, required=True)
    parser.add_argument("--sdk", type=Path, required=True)
    args = parser.parse_args()
    apply(args.engine, args.sdl, args.sdk)
