# Randomizer source notices

The generator builds selected source from tgacquin/oot3d-sariaui at
40703bf55b05ab2dda0933a5c5007730b05cebe2, including its vendored
OoT3D Randomizer at d695cf5ad78dc1990da200af601b054860d707b8.

`platform.cpp` is adapted from SariaUI's host portability layer. Its music
sequence table and shuffle implementation retain upstream provenance.
The SariaUI integration is provided under GPL-2.0-or-later; see COPYING.
The upstream randomizer's copyright and permission notice is retained in
UPSTREAM-LICENSE.md. Keep source-file notices and licenses when distributing.
The fetched source receipt records every selected file and hash.

Sources:
- https://github.com/tgacquin/oot3d-sariaui
- https://github.com/gamestabled/OoT3D_Randomizer

The generator is built from source. Players prepare game data locally. The generator contains no ROM, translated game module, or reward archive.

## Randomizer artwork

Game preparation uses [the OoT3D Randomizer artwork archive](https://github.com/gamestabled/OoT3D_Randomizer/blob/d695cf5ad78dc1990da200af601b054860d707b8/romfs/zelda_gi_melody.zar), stored here as `assets/zelda_ootr_assets.zar`. The copy included by SariaUI has the same SHA-256 digest.

C♭ made the webbed chest texture. HylianFreddy added its Skulltula symbol and contributed chest variants and ocarina-button artwork. Gamestabled contributed colored boss-key visuals. [Chest variants](https://github.com/gamestabled/OoT3D_Randomizer/pull/644), [webbed and heart chests](https://github.com/gamestabled/OoT3D_Randomizer/pull/688), [ocarina buttons](https://github.com/gamestabled/OoT3D_Randomizer/pull/719), and [boss keys](https://github.com/gamestabled/OoT3D_Randomizer/commit/c404bc27f8).
