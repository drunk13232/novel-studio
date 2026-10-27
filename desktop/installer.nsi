; -*- coding: utf-8 -*-
; Novel Studio's installer wraps the existing verified release. It never ships
; or removes author data. The program payload is generated from its manifest.
Unicode true
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"
!include "nsDialogs.nsh"
!include "StrFunc.nsh"
!include "x64.nsh"
${StrRep}

!ifndef BUILD_INCLUDE
 !error "Use desktop/build_installer.py; a verified payload include is required."
!endif
!include "${BUILD_INCLUDE}"
!ifndef MAX_INSTALL_ROOT_LENGTH
 !define MAX_INSTALL_ROOT_LENGTH 75
!endif
Name "Novel Studio ${APP_VERSION}"
OutFile "${SETUP_OUTPUT}"
InstallDir "$LOCALAPPDATA\Programs\NovelStudio\${APP_VERSION}"
RequestExecutionLevel user
SetCompressor zlib
SetDatablockOptimize on
CRCCheck on
ShowInstDetails show
ShowUninstDetails show
VIProductVersion "${APP_VERSION}.0"
VIAddVersionKey "ProductName" "Novel Studio"
VIAddVersionKey "LegalCopyright" "Copyright 2026 drunk13232"
VIAddVersionKey "FileDescription" "Novel Studio ${APP_VERSION} Setup"
VIAddVersionKey "FileVersion" "${APP_VERSION}"
VIAddVersionKey "ProductVersion" "${APP_VERSION} Preview"

Var DataDirectory
Var DataInput
Var Dialog
Var Problem
Var NoIntegration
Var JsonData

!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TEXT "$(WelcomeBody)"
!insertmacro MUI_PAGE_WELCOME
!define MUI_PAGE_CUSTOMFUNCTION_LEAVE ValidateDirectories
!insertmacro MUI_PAGE_DIRECTORY
Page custom DataPage DataPageLeave
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_TEXT "$(FinishBody)"
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "SimpChinese"
!insertmacro MUI_LANGUAGE "English"

LangString WelcomeBody ${LANG_SIMPCHINESE} "安装 Novel Studio ${APP_VERSION} Preview。$\r$\n$\r$\n程序与小说数据分开保存；旧版本不会自动卸载。安装过程不打开或修改作品。$\r$\n$\r$\n你可以选择数据目录和快捷方式。需要 Windows 10/11 x64 及 WebView2 Runtime。"
LangString WelcomeBody ${LANG_ENGLISH} "Install Novel Studio ${APP_VERSION} Preview.$\r$\n$\r$\nApplication and writing data stay separate. Older versions are retained. Setup does not open or modify manuscripts.$\r$\n$\r$\nChoose your data folder and shortcuts. Requires Windows 10/11 x64 and WebView2 Runtime."
LangString DataTitle ${LANG_SIMPCHINESE} "作品与应用数据目录"
LangString DataTitle ${LANG_ENGLISH} "Writing and application data"
LangString DataSubtitle ${LANG_SIMPCHINESE} "沿用已有目录，不迁移、不覆盖小说。"
LangString DataSubtitle ${LANG_ENGLISH} "Reuse your existing folder without moving or replacing manuscripts."
LangString DataHelp ${LANG_SIMPCHINESE} "选择现有 Novel Studio 数据目录，或指定新的独立数据目录。安装程序只记录位置，不复制或删除其中的作品。请勿选择程序安装目录。"
LangString DataHelp ${LANG_ENGLISH} "Choose an existing Novel Studio data folder, or a new separate folder. Setup only records the location; it does not copy or delete its contents. Keep it outside the application folder."
LangString Browse ${LANG_SIMPCHINESE} "浏览…"
LangString Browse ${LANG_ENGLISH} "Browse..."
LangString ProgramSection ${LANG_SIMPCHINESE} "Novel Studio 主程序（必选）"
LangString ProgramSection ${LANG_ENGLISH} "Novel Studio application (required)"
LangString DesktopSection ${LANG_SIMPCHINESE} "创建本版本桌面快捷方式"
LangString DesktopSection ${LANG_ENGLISH} "Create a version-specific desktop shortcut"
LangString StartSection ${LANG_SIMPCHINESE} "创建开始菜单快捷方式"
LangString StartSection ${LANG_ENGLISH} "Create Start menu shortcuts"
LangString FinishBody ${LANG_SIMPCHINESE} "安装完成。请从所选快捷方式或安装目录运行 NovelStudio.exe。$\r$\n$\r$\n程序将使用你选择的数据目录，不会自动进入演示项目。旧版本和作品数据均保留。"
LangString FinishBody ${LANG_ENGLISH} "Installation complete. Start NovelStudio.exe from the selected shortcuts or installation folder.$\r$\n$\r$\nIt uses your selected data folder, not the demo. Older versions and writing data are retained."
LangString InvalidTarget ${LANG_SIMPCHINESE} "安装目录必须是独立的空目录，或本安装程序创建的同版本目录；不能与数据目录重叠。请更换安装位置。"
LangString InvalidTarget ${LANG_ENGLISH} "Use a separate empty folder or the same-version folder created by this installer. Application and data folders must not overlap."
LangString PathTooLong ${LANG_SIMPCHINESE} "安装路径太长，请选择更短的文件夹（程序目录最多 ${MAX_INSTALL_ROOT_LENGTH} 个字符）。这样可以完整安装所有资源，不需要修改 Windows 设置。"
LangString PathTooLong ${LANG_ENGLISH} "Choose a shorter application folder (at most ${MAX_INSTALL_ROOT_LENGTH} characters) so every resource can be installed without changing Windows settings."
LangString InvalidData ${LANG_SIMPCHINESE} "请选择有效的绝对数据目录；路径不能包含引号、换行或制表符，不能超过 440 个字符。"
LangString InvalidData ${LANG_ENGLISH} "Choose an absolute data folder of at most 440 characters, without quotes, line breaks or tabs."
LangString NeedX64 ${LANG_SIMPCHINESE} "本版本需要 64 位 Windows。"
LangString NeedX64 ${LANG_ENGLISH} "This application requires 64-bit Windows."
LangString WriteFailed ${LANG_SIMPCHINESE} "无法写入安装文件或数据位置。请检查权限和磁盘空间，安装尚未完成。"
LangString WriteFailed ${LANG_ENGLISH} "Setup could not write application files or the data locator. Check permissions and free space. Installation is incomplete."
LangString UninstallGuard ${LANG_SIMPCHINESE} "安装归属标记不匹配，为保护文件，已停止卸载。作品数据不会被删除。"
LangString UninstallGuard ${LANG_ENGLISH} "The installation ownership marker does not match. Uninstall stopped to protect files. Writing data is not removed."

LangString CloseRunning ${LANG_SIMPCHINESE} "请先保存并正常退出这个安装目录中的 Novel Studio，再继续。安装程序不会强制关闭任何进程。"
LangString CloseRunning ${LANG_ENGLISH} "Save and close Novel Studio running from this installation directory, then retry. Setup will not force-close processes."

Function .onInit
 SetShellVarContext current
 SetRegView 64
 StrCpy $LANGUAGE ${LANG_SIMPCHINESE}
 StrCpy $NoIntegration "0"
 ${GetParameters} $0
 ClearErrors
 ${GetOptions} $0 "/NOINTEGRATION" $1
 ${IfNot} ${Errors}
  StrCpy $NoIntegration "1"
 ${EndIf}
 StrCpy $DataDirectory "${DEFAULT_DATA_DIRECTORY}"
 ClearErrors
 ${GetOptions} $0 "/DATADIR=" $1
 ${IfNot} ${Errors}
  StrCpy $DataDirectory $1
 ${EndIf}
 ${IfNot} ${RunningX64}
  MessageBox MB_OK|MB_ICONSTOP "$(NeedX64)" /SD IDOK
  SetErrorLevel 2
  Quit
 ${EndIf}
FunctionEnd

Function DataPage
 !insertmacro MUI_HEADER_TEXT "$(DataTitle)" "$(DataSubtitle)"
 nsDialogs::Create 1018
 Pop $Dialog
 ${If} $Dialog == error
  Abort
 ${EndIf}
 ${NSD_CreateLabel} 0 0 100% 48u "$(DataHelp)"
 Pop $0
 ${NSD_CreateDirRequest} 0 58u 82% 14u "$DataDirectory"
 Pop $DataInput
 ${NSD_CreateBrowseButton} 84% 58u 16% 14u "$(Browse)"
 Pop $0
 ${NSD_OnClick} $0 DataBrowse
 nsDialogs::Show
FunctionEnd
Function DataBrowse
 nsDialogs::SelectFolderDialog "$(DataTitle)" "$DataDirectory"
 Pop $0
 ${If} $0 != error
  StrCpy $DataDirectory $0
  ${NSD_SetText} $DataInput "$DataDirectory"
 ${EndIf}
FunctionEnd
Function DataPageLeave
 ${NSD_GetText} $DataInput $DataDirectory
 Call ValidateDirectories
FunctionEnd

Function ValidateDirectories
 StrCpy $Problem ""
 ${If} $DataDirectory == ""
  StrCpy $Problem "$(InvalidData)"
 ${EndIf}
 StrLen $0 $DataDirectory
 ${If} $0 > 440
  StrCpy $Problem "$(InvalidData)"
 ${EndIf}
 ${GetRoot} "$DataDirectory" $0
 ${If} $0 == ""
  StrCpy $Problem "$(InvalidData)"
 ${EndIf}
 ${StrRep} $0 $DataDirectory '$\"' ''
 ${If} $0 != $DataDirectory
  StrCpy $Problem "$(InvalidData)"
 ${EndIf}
 ${StrRep} $0 $DataDirectory '$\r' ''
 ${If} $0 != $DataDirectory
  StrCpy $Problem "$(InvalidData)"
 ${EndIf}
 ${StrRep} $0 $DataDirectory '$\n' ''
 ${If} $0 != $DataDirectory
  StrCpy $Problem "$(InvalidData)"
 ${EndIf}
 ${StrRep} $0 $DataDirectory '$\t' ''
 ${If} $0 != $DataDirectory
  StrCpy $Problem "$(InvalidData)"
 ${EndIf}
 ; Win32 normalization also supports not-yet-created directories; NSIS's
 ; GetFullPathName instruction requires an existing path portion.
 System::Call 'kernel32::GetFullPathNameW(w "$INSTDIR", i ${NSIS_MAX_STRLEN}, w .r0, p 0) i.r1'
 ${If} $1 == 0
 ${OrIf} $1 >= ${NSIS_MAX_STRLEN}
  StrCpy $Problem "$(InvalidTarget)"
 ${Else}
  StrCpy $INSTDIR $0
 ${EndIf}
 System::Call 'kernel32::GetFullPathNameW(w "$DataDirectory", i ${NSIS_MAX_STRLEN}, w .r0, p 0) i.r1'
 ${If} $1 == 0
 ${OrIf} $1 >= ${NSIS_MAX_STRLEN}
  StrCpy $Problem "$(InvalidData)"
 ${Else}
  StrCpy $DataDirectory $0
 ${EndIf}
 StrLen $0 $INSTDIR
 ${If} $0 > ${MAX_INSTALL_ROOT_LENGTH}
  StrCpy $Problem "$(PathTooLong)"
 ${EndIf}
 StrCpy $0 "$INSTDIR\"
 StrCpy $1 "$DataDirectory\"
 StrLen $2 $0
 StrCpy $3 $1 $2
 ${If} $0 == $3
  StrCpy $Problem "$(InvalidTarget)"
 ${EndIf}
 StrLen $2 $1
 StrCpy $3 $0 $2
 ${If} $1 == $3
  StrCpy $Problem "$(InvalidTarget)"
 ${EndIf}
 ${GetRoot} "$INSTDIR" $0
 ${If} $INSTDIR == $0
 ${OrIf} $INSTDIR == "$0\"
  StrCpy $Problem "$(InvalidTarget)"
 ${EndIf}
 ; Never accept an existing unrelated directory, even in silent mode.
 IfFileExists "$INSTDIR\setup-owner.ini" check_owner check_empty
 check_owner:
  ReadINIStr $0 "$INSTDIR\setup-owner.ini" "Setup" "Version"
  ReadINIStr $1 "$INSTDIR\setup-owner.ini" "Setup" "Directory"
  ${If} $0 != "${APP_VERSION}"
  ${OrIf} $1 != $INSTDIR
   StrCpy $Problem "$(InvalidTarget)"
  ${EndIf}
  Goto checked_target
 check_empty:
  StrCpy $1 ""
  ClearErrors
  FindFirst $0 $1 "$INSTDIR\*.*"
  IfErrors checked_target
  ${DoWhile} $1 != ""
   ${If} $1 != "."
   ${AndIf} $1 != ".."
    StrCpy $Problem "$(InvalidTarget)"
   ${EndIf}
   FindNext $0 $1
  ${Loop}
  FindClose $0
 checked_target:
 ; A running executable cannot be reopened for writing on Windows. Do not
 ; kill any process or start replacing files while this version is in use.
 IfFileExists "$INSTDIR\NovelStudio.exe" 0 executable_checked
 ClearErrors
 FileOpen $0 "$INSTDIR\NovelStudio.exe" a
 IfErrors executable_locked
 FileClose $0
 Goto executable_checked
 executable_locked:
  StrCpy $Problem "$(CloseRunning)"
 executable_checked:
 ${If} $Problem != ""
  MessageBox MB_OK|MB_ICONSTOP "$Problem" /SD IDOK
  IfSilent 0 +3
   SetErrorLevel 2
   Quit
  Abort
 ${EndIf}
FunctionEnd

Function WriteDataLocator
 ${StrRep} $JsonData $DataDirectory '\' '\\'
 ${StrRep} $JsonData $JsonData '$\"' '\$\"'
 StrCpy $0 '{$\"data$\":$\"$JsonData$\"}$\r$\n'
 ClearErrors
 FileOpen $1 "$INSTDIR\data-location.json" w
 IfErrors write_error
 System::Call 'kernel32::WideCharToMultiByte(i 65001, i 0, w r0, i -1, p 0, i 0, p 0, p 0) i.r3'
 System::Alloc $3
 Pop $2
 ${If} $2 == 0
  FileClose $1
  Goto write_error
 ${EndIf}
 System::Call 'kernel32::WideCharToMultiByte(i 65001, i 0, w r0, i -1, p r2, i r3, p 0, p 0) i.r4'
 IntOp $3 $3 - 1
 System::Call 'kernel32::WriteFile(p r1, p r2, i r3, *i .r4, p 0) i.r5'
 System::Free $2
 FileClose $1
 ${If} $5 == 0
 ${OrIf} $4 != $3
  Goto write_error
 ${EndIf}
 Return
 write_error:
  MessageBox MB_OK|MB_ICONSTOP "$(WriteFailed)" /SD IDOK
  SetErrorLevel 3
  Abort
FunctionEnd

Section "$(ProgramSection)" SEC_APP
 SectionIn RO
 Call ValidateDirectories
 SetOutPath "$INSTDIR"
 SetOverwrite on
 ClearErrors
 ; Own the initially empty directory before extraction so interrupted setup
 ; can be retried, without accepting any unrelated pre-existing folder.
 WriteINIStr "$INSTDIR\setup-owner.ini" "Setup" "Version" "${APP_VERSION}"
 WriteINIStr "$INSTDIR\setup-owner.ini" "Setup" "Directory" "$INSTDIR"
 WriteINIStr "$INSTDIR\setup-owner.ini" "Setup" "NoIntegration" "$NoIntegration"
 WriteUninstaller "$INSTDIR\Uninstall.exe"
 !insertmacro InstallVerifiedPayload
 ${If} ${Errors}
  MessageBox MB_OK|MB_ICONSTOP "$(WriteFailed)" /SD IDOK
  SetErrorLevel 3
  Abort
 ${EndIf}
 Call WriteDataLocator
 WriteINIStr "$INSTDIR\setup-owner.ini" "Setup" "Version" "${APP_VERSION}"
 WriteINIStr "$INSTDIR\setup-owner.ini" "Setup" "Directory" "$INSTDIR"
 WriteINIStr "$INSTDIR\setup-owner.ini" "Setup" "NoIntegration" "$NoIntegration"
 WriteUninstaller "$INSTDIR\Uninstall.exe"
 ${If} $NoIntegration == "0"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NovelStudio-${APP_VERSION}" "DisplayName" "Novel Studio ${APP_VERSION} Preview"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NovelStudio-${APP_VERSION}" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NovelStudio-${APP_VERSION}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NovelStudio-${APP_VERSION}" "UninstallString" '$\"$INSTDIR\Uninstall.exe$\"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NovelStudio-${APP_VERSION}" "DisplayIcon" "$INSTDIR\NovelStudio.exe"
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NovelStudio-${APP_VERSION}" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NovelStudio-${APP_VERSION}" "NoRepair" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NovelStudio-${APP_VERSION}" "EstimatedSize" ${PAYLOAD_KB}
 ${EndIf}
SectionEnd
Section "$(DesktopSection)" SEC_DESKTOP
 ${If} $NoIntegration == "0"
  CreateShortcut "$DESKTOP\Novel Studio ${APP_VERSION}.lnk" "$INSTDIR\NovelStudio.exe" "" "$INSTDIR\NovelStudio.exe"
  WriteINIStr "$INSTDIR\setup-owner.ini" "Setup" "DesktopShortcut" "1"
 ${EndIf}
SectionEnd
Section "$(StartSection)" SEC_START
 ${If} $NoIntegration == "0"
  CreateDirectory "$SMPROGRAMS\Novel Studio ${APP_VERSION}"
  CreateShortcut "$SMPROGRAMS\Novel Studio ${APP_VERSION}\Novel Studio.lnk" "$INSTDIR\NovelStudio.exe" "" "$INSTDIR\NovelStudio.exe"
  CreateShortcut "$SMPROGRAMS\Novel Studio ${APP_VERSION}\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
  WriteINIStr "$INSTDIR\setup-owner.ini" "Setup" "StartShortcut" "1"
 ${EndIf}
SectionEnd

Function un.onInit
 SetShellVarContext current
 SetRegView 64
 ReadINIStr $0 "$INSTDIR\setup-owner.ini" "Setup" "Version"
 ReadINIStr $1 "$INSTDIR\setup-owner.ini" "Setup" "Directory"
 ${If} $0 != "${APP_VERSION}"
 ${OrIf} $1 != $INSTDIR
  MessageBox MB_OK|MB_ICONSTOP "$(UninstallGuard)" /SD IDOK
  SetErrorLevel 2
  Quit
 ${EndIf}
 IfFileExists "$INSTDIR\NovelStudio.exe" 0 un_executable_checked
 ClearErrors
 FileOpen $0 "$INSTDIR\NovelStudio.exe" a
 IfErrors un_executable_locked
 FileClose $0
 Goto un_executable_checked
 un_executable_locked:
  MessageBox MB_OK|MB_ICONSTOP "$(CloseRunning)" /SD IDOK
  SetErrorLevel 2
  Quit
 un_executable_checked:
FunctionEnd
Section "Uninstall"
 ReadINIStr $NoIntegration "$INSTDIR\setup-owner.ini" "Setup" "NoIntegration"
 ${If} $NoIntegration == "0"
  ReadRegStr $0 HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NovelStudio-${APP_VERSION}" "InstallLocation"
  ${If} $0 == $INSTDIR
   DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NovelStudio-${APP_VERSION}"
  ${EndIf}
  ReadINIStr $0 "$INSTDIR\setup-owner.ini" "Setup" "DesktopShortcut"
  ${If} $0 == "1"
   Delete "$DESKTOP\Novel Studio ${APP_VERSION}.lnk"
  ${EndIf}
  ReadINIStr $0 "$INSTDIR\setup-owner.ini" "Setup" "StartShortcut"
  ${If} $0 == "1"
   Delete "$SMPROGRAMS\Novel Studio ${APP_VERSION}\Novel Studio.lnk"
   Delete "$SMPROGRAMS\Novel Studio ${APP_VERSION}\Uninstall.lnk"
   RMDir "$SMPROGRAMS\Novel Studio ${APP_VERSION}"
  ${EndIf}
 ${EndIf}
 !insertmacro UninstallVerifiedPayload
 Delete "$INSTDIR\data-location.json"
 Delete "$INSTDIR\setup-owner.ini"
 Delete "$INSTDIR\Uninstall.exe"
 ; Non-recursive: files created by the author are never swept away.
 RMDir "$INSTDIR"
SectionEnd
