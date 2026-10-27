Companion portrait slots — local personal use

The app reads companion/manifest.json in its user data directory first.
Source development without NOVEL_STUDIO_DATA uses web/runtime/studio/companion/.
Fallback slots live in web/frontend/public/companion/ (source) or
_internal/resources/frontend/companion/ (installed resources).

Example:
{"schema_version":1,"yoshino":"yoshino.png","rem":"rem.png"}

Place your local image beside manifest.json. Settings > Appearance > Character
portraits > Reload portraits updates all mounted cards; restarting also works.
Rem day and night share the same file. Cards show the complete portrait without
cover-cropping; they can collapse, and focus mode hides them.

PNG/WebP/JPEG only. Plain ASCII filenames, no directories or remote URLs.
Maximum 8 MiB and 6 million pixels per image. Recommended: at most 1024x1536.
Missing, invalid or corrupt images show an explicit named portrait placeholder.

Public builds must keep both manifest slots null and ship only this guide and
manifest.json. Personal character artwork stays outside installation/source ZIPs.
The visual companion does not select an AI persona or change model permissions.
