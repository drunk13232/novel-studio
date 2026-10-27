# Character portrait companion supplement (2.10.2)

This supplement reuses the original companion components, nine themes and
appearance preferences. It does not change the editor or story data.

## Visible character slots

Yoshino selects the Yoshino portrait. Rem day and Rem night select the same Rem
portrait. Welcome/bookshelf: a full standing portrait beside the welcome copy.
Writing: a small collapsible standing portrait inside the existing navigation.
Assistant and roleplay: a standing portrait beside the identity introduction.
Images use `object-fit: contain`; they never overlay the manuscript. Every card
can collapse and reopen. Existing focus/decorations controls hide them.

When no image is configured, the slot explicitly states the character name and
"Add a character portrait", with a neutral silhouette. It does not claim to show
the character using decorative motifs.

## Personal resources

Use `companion/manifest.json` under the application data directory. Images sit
beside this manifest. Example:

```json
{"schema_version":1,"yoshino":"yoshino.png","rem":"rem.png"}
```

Settings -> Appearance -> Character portraits -> Reload portraits refreshes all
mounted portrait cards. Restarting also reloads the manifest. Rem variants share
one slot. Filenames only: PNG/WebP/JPEG, no URL or folder. Maximum 8 MiB / 6 million
pixels per image. Suggested maximum 1024x1536, transparent PNG/WebP.

The backend provides a typed manifest and two read-only image endpoints using the
existing loopback/origin security middleware. It validates path containment,
rejects symlinks/reparse points, validates actual raster format and dimensions,
and never returns a filesystem path. No arbitrary file upload/read endpoint is
introduced. Invalid or missing images remain a clearly labelled placeholder.

## Personal vs public

Personal files stay outside the executable bundle. Source, PyInstaller and ZIP
packagers reject companion resources unless only README.txt and an empty manifest
are present. This prevents a local personal portrait from silently entering a
public candidate. Images created for a personal version are not automatically
cleared for redistribution and are not official character artwork.

No model is invoked to display a portrait, and no new dependency is installed.
The user can replace each file without changing theme layout or code.
