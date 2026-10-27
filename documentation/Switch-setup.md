# Experimental Switch setup

The Switch version is being prepared for an experimental Preview. It has been
tested in emulation; physical Switch performance remains unverified.

## Optional custom textures

**Use the mobile version of Henriko's texture pack for Switch.** Its smaller
textures are better suited to the Switch's available memory than the desktop
pack. Supply your own copy; no texture pack is included in the download.

During desktop preparation, select the extracted mobile pack. It is copied to
`switch/oot3dre/textures` on the prepared SD layout. Keep its directory structure
intact. In the game, open **Minus → Graphics → Use custom textures** to enable it.
Use **Reload** after replacing the pack's files.

The bundled HD dialogue fonts work independently of the texture pack. A title
screen's “4K” label is not a reliable check that all replacements are loading.

Keep **30 FPS** as the default. **60 FPS** is an experimental interpolation option.

## Player models

Optionally add `--child-model /path/to/child.pak`, `--adult-model /path/to/adult.pak`, or both to the preparation command. These accept human-rig OoT PAKs or ZOBJs. Conversion requires NumPy 2.3.2 (`python3 -m pip install numpy==2.3.2`) in the Python environment running preparation.

Models are included only in your private prepared game. Omit a model option to use Original Link for that age. Export a new prepared game to change models; retain your existing SD-card saves and settings. Package scripts, custom animations, and sounds are not imported.
