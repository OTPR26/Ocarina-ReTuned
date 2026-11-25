"""Link two locally prepared titles without sharing their generated functions."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import tempfile


def combine(normal, randomized, output, tools, suffix=''):
    normal, randomized, output = map(Path, (normal, randomized, output))
    if output.exists() or normal.resolve() == randomized.resolve():
        raise ValueError('Choose two distinct title archives and a new output')
    def run(tool, *arguments):
        subprocess.run([str(tools / ('aarch64-none-elf-' + tool + suffix)), *arguments], check=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        root = Path(temp)
        # Resolve COMDAT groups within this title first. Localizing symbols
        # afterward prevents identically named guest functions binding across titles.
        obj = root / 'randomized.o'
        run('ld', '-r', '--force-group-allocation', '--whole-archive', randomized,
            '--no-whole-archive', '-o', obj)
        query = 'retuned_switch_randomizer_query'
        run('objcopy', '--redefine-sym', 'triaevum_title_whole_aot_query=' + query,
            '--keep-global-symbol', query, obj)
        nm = tools / ('aarch64-none-elf-nm' + suffix)
        symbols = subprocess.check_output([nm, '-g', '--defined-only', obj], text=True)
        if [line.split()[-1] for line in symbols.splitlines() if line.strip()] != [query]:
            raise ValueError('Randomizer title isolation failed')
        # The final recipe uses --whole-archive, including the weakly queried title.
        with randomized.open('rb') as archive:
            identity = hashlib.file_digest(archive, 'sha256').hexdigest()
        source = root / 'identity.c'
        source.write_text(f'const char retuned_switch_randomizer_id[] = "{identity}";\n')
        marker = root / 'identity.o'
        run('gcc', '-fPIC', '-c', source, '-o', marker)
        merged = root / 'combined.a'
        shutil.copyfile(normal, merged)
        run('ar', 'qcs', merged, obj, marker)
        merged.rename(output)

def stage_data(manifest_path, randomized, output):
    """Stage the matching private game image and a compact static-title identity."""
    from stage_runtime import digest, verified_game_image
    manifest = json.loads(manifest_path.read_text())
    proof = manifest['randomizer_proof']
    binding = json.loads(Path(str(randomized) + '.randomizer.json').read_text())
    archive_id = digest(randomized)
    seed = manifest_path.parent / 'seed.json'
    layout = json.dumps(proof['seed_layout'], sort_keys=True, separators=(',', ':')).encode()
    if (not verified_game_image(manifest) or proof['seed_file'] != 'seed.json'
            or digest(seed) != proof['seed_sha256']
            or binding != dict(format='retuned-randomizer-module-v2', module_sha256=archive_id,
                               code_sha256=manifest['source']['code_bin_sha256'],
                               seed_layout_sha256=hashlib.sha256(layout).hexdigest())):
        raise ValueError('Switch Randomizer archive and image binding do not match')
    proof['activation_allowed'] = True
    output.mkdir(parents=True)
    for key, value in list(manifest['source'].items()):
        if not key.endswith('_path'):
            continue
        source = manifest_path.parent / value
        dest = output / (key[:-5] + '.bin')
        shutil.copyfile(source, dest)
        expected = manifest['source'].get(key[:-5] + '_sha256') or digest(source)
        if digest(dest) != expected:
            raise ValueError('Switch Randomizer resource checksum mismatch')
        manifest['source'][key] = dest.name
    (output / 'process-manifest.json').write_text(json.dumps(manifest))
    shutil.copyfile(seed, output / 'seed.json')
    marker = output / 'title.id'
    marker.write_text(archive_id)
    binding['module_sha256'] = digest(marker)
    (output / 'title.id.randomizer.json').write_text(json.dumps(binding))
