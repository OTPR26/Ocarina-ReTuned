Interface typography

Reference: TwilitRealm/dusklight at 77705f8bb95ef7b7dca4675b149c4bcb6a48da34.
Font binaries are unmodified. Each family retains its accompanying SIL Open Font License.
Pinned download URLs and SHA-256 hashes are in sources.json.

Fira Sans: menu body (15 logical units) and startup body (20).
Fira Sans Condensed: headings (20) and startup buttons (32, reduced only to fit short windows).
Alegreya SC: startup display title (32).

Android uses display density and system text scaling for its native screens.
The shared frontend converts logical sizes to the rendering surface and rasterizes fonts for display density.
Desktop windows retain their logical text size when resized; the layout constrains button sizes to available space.
The existing Menu size control remains available.

Dialogue fonts and game texture lettering are separate from interface typography.
