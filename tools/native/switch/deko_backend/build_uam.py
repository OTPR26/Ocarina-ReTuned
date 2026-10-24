"""Build and isolate the pinned Switch uam compiler in a private build folder."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess


def build(source: Path, output: Path, sdk: Path):
    source, output, sdk = source.resolve(), output.resolve(), sdk.absolute()
    output.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, DEVKITPRO=str(sdk), DEVKITA64=str(sdk / "devkitA64"))
    prefix_hook=output / "reproducible-paths.cmake"
    prefix_hook.write_text('foreach(mapping "$ENV{HOME}=/user" "' + str(sdk.resolve()) + '=/sdk" "' + str(sdk) + '=/sdk" "${CMAKE_BINARY_DIR}=/build" "${CMAKE_SOURCE_DIR}=/uam")\n'
                          'add_compile_options("-ffile-prefix-map=${mapping}" "-fmacro-prefix-map=${mapping}")\nendforeach()\n')
    subprocess.run(["cmake", "-S", str(source), "-B", str(output), "-G", "Ninja",
                    "-DCMAKE_TOOLCHAIN_FILE=" + str(sdk / "cmake/Switch.cmake"),
                    "-DNX_ROOT=" + str(sdk), "-DCMAKE_BUILD_TYPE=Release",
                    "-DCMAKE_PROJECT_uam_INCLUDE=" + str(prefix_hook)], env=env, check=True)
    subprocess.run(["cmake", "--build", str(output), "--target", "uamlib", "-j3"], env=env, check=True)
    tools = sdk / "devkitA64/bin"
    archive = output / "libuamlib.a"
    symbols = subprocess.check_output([str(tools / "aarch64-none-elf-nm"), "-g", "--defined-only", str(archive)], text=True)
    names = set()
    for line in symbols.splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[1] in "ABCDGIRSTVW":
            name = fields[2]
            if not name.startswith("_ZN3uam"):
                names.add(name)
    mapping = output / "uam-symbol-map.txt"
    mapping.write_text("".join(f"{n} retuned_uam_{n}\n" for n in sorted(names)))
    target = output / "libretuned_uam.a"
    subprocess.run([str(tools / "aarch64-none-elf-objcopy"), "--redefine-syms=" + str(mapping), str(archive), str(target)], check=True)
    receipt = {"symbol_count": len(names), "archive_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
               "purpose": "Keep compiler Mesa globals separate from SDL EGL globals", "public_package": False}
    (output / "compiler-build-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--sdk", type=Path, required=True)
    args = p.parse_args()
    build(args.source, args.output, args.sdk)
