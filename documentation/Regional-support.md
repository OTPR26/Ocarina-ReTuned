# Regional ROM support

Preview 0.5.8 supports the pinned USA and European inputs. Asian regional support remains on the roadmap for [issue #13](https://github.com/OTPR26/Ocarina-ReTuned/issues/13).

| Region | Development status |
|---|---|
| USA | Existing preparation path retained, including reuse of verified caches from previous versions. |
| Europe | Verified preparation, activation, and Italian gameplay tested locally. English, German, French, Spanish, and Italian resources are available; original localized messages are preserved. |
| Japan | Input audited. Executable adaptation, Japanese fonts, and localized resource routing need integration. |
| Korea and Taiwan | Inputs audited. These use a different executable layout and version-5 message containers; both need adapters before native preparation can accept them. |

Regional support uses the same shared preparation pipeline on each platform. Cache keys include the source region, verified content identities, and normalized output hashes. Automatic updates retain the region recorded in the activated launch profile; selecting a different ROM does not change that profile until preparation succeeds.

Asian resources must retain their original text and glyph coverage. Adding ROM hashes to the catalog alone would not provide working support. Additional revisions also require their own verified identities and compatibility checks.
