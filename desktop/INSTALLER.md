# Windows installation wizard

The optional NSIS Setup.exe installs the existing verified PyInstaller application. It does not rebuild the editor or add runtime services. This installer is per-user and does not require an administrator account.

## Build

Use a verified official portable NSIS 3.13 compiler (HTTPS download, checked archive hash). The compiler is a development tool and is not placed in the application payload.

```powershell
& ./web/backend/.venv/Scripts/python.exe desktop/build_installer.py --makensis <NSIS-directory>/makensis.exe
```

The default data location is the current user's LocalAppData/NovelStudio folder. For a private local build only, `--data-default <existing-data-folder>` preselects that path in the wizard; it does not include the folder's contents. Do not distribute a personally configured installer as a sanitized public candidate without another review.

Output: `release/v<version>/NovelStudio-<version>-Setup.exe`, adjacent metadata and SHA-256. Existing installer outputs are never silently overwritten by the builder. Source payload files are verified against the existing release manifest before compilation. Sealed Windows and Developer ZIPs remain untouched.

## User flow

Welcome → application directory → data directory → optional desktop/Start menu shortcuts → install → finish. The installed application uses the selected data folder and does not automatically enter the demo. It does not auto-launch at the end of installation. Desktop and Start menu entries have version-specific names, retaining older entries and application folders.

The program directory must be empty or owned by this same-version installer, and cannot overlap the selected data directory. The current payload requires an application-folder path of at most 75 UTF-16 characters so all nested resources fit legacy Windows path limits; longer folders are rejected before file extraction, without changing system settings. A running executable blocks replacement/uninstall; no processes are force-closed. Ownership is recorded before extraction so an interrupted install can be retried.

Uninstall removes the fixed list of installed program files and its own selected integrations. It does not recursively remove directories; extra files and external user data are retained. A moved/mismatched ownership marker stops uninstallation.

## Isolated checks

`/S /NOINTEGRATION /DATADIR="<isolated-data>" /D=<isolated-program>` permits silent local verification without desktop, Start menu or registry integration. NSIS requires `/D=` last and unquoted. Use only new isolated directories. Never test installs/uninstalls against real works.

The application requires Windows x64 and Microsoft WebView2 Runtime. Setup does not download prerequisites, models or AI services. No signing or publication claim is made. NSIS notices are preserved. Original Novel Studio software is Apache-2.0, Copyright 2026 drunk13232; third-party and user-created assets keep their own terms.


The compiler input uses the standard Windows extended-length namespace when extracted source paths are deep. This does not change installed filenames or raise the existing application-folder length limit, and does not modify the Windows registry. Original payload hashes are verified before compilation and after the isolated installation check.
