Liberation Sans 1.07.4 font source and distribution notice

PDF.js 6.3.289 contains the four original npm LiberationSans TTF resources.
They are governed by LICENSE_LIBERATION (GPL version 2 with the Liberation
font exception), independently from the Novel Studio project license.
This folder provides the complete upstream 1.07.4 SFD source archive,
including COPYING, License.txt, AUTHORS, Makefile and font export scripts.
The fonts can be edited/rebuilt with FontForge as described by the upstream
README. The runtime TTF files are replaceable local data resources, not
compiled inside NovelStudio.exe. Do not substitute other TTF builds without
also respecting PDF.js glyph-order and width-table compatibility.

Official source:
https://releases.pagure.org/liberation-fonts/liberation-fonts-1.07.4.tar.gz
SHA-256: ad98b7498dc2992f7f0868f79b65ce4a720a3acdb63ab3f1f1cb6881117a5406
Upstream project: https://github.com/liberationfonts/liberation-1.7-fonts
PDF.js font notice:
https://github.com/mozilla/pdf.js/blob/v6.3.289/external/standard_fonts/README.md

The npm TTF bytes differ from another official 1.07.4 binary release.
668 shared Unicode character outlines in each face match exactly in the
FontTools audit. This establishes resource provenance and glyph agreement,
not a promise of a bit-reproducible upstream compiler/toolchain.
No TTF has been modified or substituted by Novel Studio.
