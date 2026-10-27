# Player models

Open **Settings → Mods → PAK Importer** before starting gameplay on Android, Windows, Mac, or Linux. Choose Child or Adult, then import a human-rig OoT `.pak` or `.zobj`. Each age has its own selection. **Original Link** restores that age’s original appearance while retaining its imported model for later use.

On desktop, the game closes before opening the model manager and reopens when you finish. The complete Preview includes the conversion tools; no separate Python packages are needed.

For iOS, tvOS, and Switch, include models during desktop game preparation. Add `--child-model "/path/to/child.pak"`, `--adult-model "/path/to/adult.pak"`, or both to the platform’s preparation command. Apple preparation still requires a Mac and Xcode. The converted model is included in your private prepared game. Omit an option to use Original Link for that age. Changing a model on these platforms requires exporting the prepared game again.

The importer reads model geometry and textures. Package scripts, custom animations, and sounds are not run or imported. Native equipment and the game’s animation skeleton are retained. Other rigs and models needing external shared assets are unsupported.

Model imports update game assets without recompiling the native game module. Saves, settings, and texture-folder selections are retained. Android and desktop preparation updates reapply verified model selections; if the underlying native actor changes, reimport the model.

The bounded F3DEX2 and N64 texture readers are adapted from AgitationSkeleton’s `soh_modloaderconverter_public`, revision `cd971b52cfbf2e90d9132cd7475b6a0cb85dd8ad`, under MIT. Its license and notice accompany the importer. No player-model packages or game assets are bundled.
