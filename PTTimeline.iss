; PTTimeline.iss
; Inno Setup installer script for PTTimeline suite
; Applications: PTTEdit, PTTPlot, PTTView
; Publisher:    RNCSoftware
; Author:       Richard Carver
; Version:      0.3.2.8-dev

#define AppName        "PTTimeline"
#define AppVersion     "0.3.2.8-dev"
#define AppVerName     "PTTimeline 0.3.2.8-dev"
#define AppPublisher   "RNCSoftware"
#define AppAuthor      "Richard Carver"
#define AppCopyright   "Copyright (C) 2026 Richard Carver"
#define AppURL         "https://www.rncsoftware.com"
#define SourceDir      "dist\PTTimeline"
#define ResourcesDir   "dist\PTTimeline\resources"
#define SamplesDir     "dist\PTTimeline\samples"

[Setup]
AppId                    ={{32C35BAB-6BA6-4E60-B632-5CD063F67C50}
AppName                  ={#AppName}
AppVersion               ={#AppVersion}
AppVerName               ={#AppVerName}
AppPublisher             ={#AppPublisher}
AppPublisherURL          ={#AppURL}
AppSupportURL            ={#AppURL}
AppUpdatesURL            ={#AppURL}
AppCopyright             ={#AppCopyright}
DefaultDirName           ={commonpf}\{#AppPublisher}\{#AppName}
DefaultGroupName         ={#AppName}
DisableProgramGroupPage  =no
OutputDir                =installer
OutputBaseFilename       =PTTimeline-0.3.2.8-dev-setup
SetupIconFile            ={#ResourcesDir}\PTTimeline.ico
LicenseFile              =license.txt
Compression              =lzma2/ultra64
SolidCompression         =yes
WizardStyle              =modern
PrivilegesRequired       =admin
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon     ={app}\resources\PTTimeline.ico
UninstallDisplayName     ={#AppVerName}
MinVersion               =10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

; -----------------------------------------------------------------------------
; COMPONENTS
; -----------------------------------------------------------------------------

[Components]
Name: "main";    Description: "PTTimeline Applications (required)"; Types: full compact custom; Flags: fixed
Name: "samples"; Description: "Sample timeline files (installed to Public Documents)"; Types: full

; -----------------------------------------------------------------------------
; TASKS
; -----------------------------------------------------------------------------

[Tasks]
Name: "desktopicons"; Description: "Create &desktop shortcuts"; GroupDescription: "Additional icons:"; Flags: unchecked

; -----------------------------------------------------------------------------
; FILES
; -----------------------------------------------------------------------------

[Files]
; Main executables
Source: "{#SourceDir}\pttedit.exe";  DestDir: "{app}"; Flags: ignoreversion; Components: main
Source: "{#SourceDir}\pttplot.exe";  DestDir: "{app}"; Flags: ignoreversion; Components: main
Source: "{#SourceDir}\pttview.exe";  DestDir: "{app}"; Flags: ignoreversion; Components: main

; PyInstaller shared runtime
Source: "{#SourceDir}\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main

; Icons / resources
Source: "{#ResourcesDir}\*"; DestDir: "{app}\resources"; Flags: ignoreversion; Components: main

; Sample data files — optional, installed to Public Documents (not program folder)
Source: "{#SamplesDir}\*"; DestDir: "{commondocs}\RNCSoftware\PTTimeline\Samples"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: samples

; Documentation
Source: "dist\PTTimeline\docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion; Components: main

; License (stored in install dir for reference)
Source: "license.txt"; DestDir: "{app}"; Flags: ignoreversion; Components: main

; -----------------------------------------------------------------------------
; DIRECTORIES
; -----------------------------------------------------------------------------

[Dirs]
; Samples folder — created by component, removed on uninstall if empty
Name: "{commondocs}\RNCSoftware\PTTimeline\Samples"; Components: samples; Flags: uninsalwaysuninstall

; -----------------------------------------------------------------------------
; START MENU SHORTCUTS
; -----------------------------------------------------------------------------

[Icons]
; Start Menu - PTTimeline group
Name: "{group}\PTTEdit";              Filename: "{app}\pttedit.exe"; IconFilename: "{app}\resources\pttedit.ico";    Comment: "Process-Task Timeline Editor"
Name: "{group}\PTTPlot";              Filename: "{app}\pttplot.exe"; IconFilename: "{app}\resources\pttplot.ico";    Comment: "Process-Task Timeline Plotter"
Name: "{group}\PTTView";              Filename: "{app}\pttview.exe"; IconFilename: "{app}\resources\pttview.ico";    Comment: "Process-Task Timeline Viewer"
Name: "{group}\Sample Files";         Filename: "{commondocs}\RNCSoftware\PTTimeline\Samples";                                                    Comment: "PTTimeline sample timeline files"; Components: samples
Name: "{group}\Uninstall PTTimeline"; Filename: "{uninstallexe}";   IconFilename: "{app}\resources\PTTimeline.ico"

; Desktop shortcuts — optional, installed directly on desktop (user choice during install)
Name: "{commondesktop}\PTTEdit";  Filename: "{app}\pttedit.exe"; IconFilename: "{app}\resources\pttedit.ico"; Comment: "Process-Task Timeline Editor";  Tasks: desktopicons
Name: "{commondesktop}\PTTPlot";  Filename: "{app}\pttplot.exe"; IconFilename: "{app}\resources\pttplot.ico"; Comment: "Process-Task Timeline Plotter"; Tasks: desktopicons
Name: "{commondesktop}\PTTView";  Filename: "{app}\pttview.exe"; IconFilename: "{app}\resources\pttview.ico"; Comment: "Process-Task Timeline Viewer";  Tasks: desktopicons

; -----------------------------------------------------------------------------
; FILE ASSOCIATIONS
; -----------------------------------------------------------------------------

[Registry]
; .pttd -> PTTEdit
Root: HKCR; Subkey: ".pttd";                              ValueType: string; ValueName: ""; ValueData: "PTTimeline.pttd";      Flags: uninsdeletevalue
Root: HKCR; Subkey: "PTTimeline.pttd";                    ValueType: string; ValueName: ""; ValueData: "PTTimeline Data File"; Flags: uninsdeletekey
Root: HKCR; Subkey: "PTTimeline.pttd\DefaultIcon";        ValueType: string; ValueName: ""; ValueData: "{app}\resources\pttedit.ico,0"
Root: HKCR; Subkey: "PTTimeline.pttd\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\pttedit.exe"" ""%1"""

; .pttp -> PTTPlot
Root: HKCR; Subkey: ".pttp";                              ValueType: string; ValueName: ""; ValueData: "PTTimeline.pttp";       Flags: uninsdeletevalue
Root: HKCR; Subkey: "PTTimeline.pttp";                    ValueType: string; ValueName: ""; ValueData: "PTTimeline Plot File"; Flags: uninsdeletekey
Root: HKCR; Subkey: "PTTimeline.pttp\DefaultIcon";        ValueType: string; ValueName: ""; ValueData: "{app}\resources\pttplot.ico,0"
Root: HKCR; Subkey: "PTTimeline.pttp\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\pttplot.exe"" ""%1"""

; Notify Windows shell of file association changes
Root: HKCR; Subkey: ".pttd"; ValueType: string; ValueName: "PerceivedType"; ValueData: "document"
Root: HKCR; Subkey: ".pttp"; ValueType: string; ValueName: "PerceivedType"; ValueData: "document"

; -----------------------------------------------------------------------------
; CODE — prompt user if sample files already exist on reinstall/upgrade
; -----------------------------------------------------------------------------

[Code]
// Checks whether the samples destination folder exists and contains any files.
function SamplesFolderHasFiles(): Boolean;
var
  FindRec: TFindRec;
  SamplesPath: String;
begin
  Result := False;
  SamplesPath := ExpandConstant('{commondocs}\RNCSoftware\PTTimeline\Samples');
  if DirExists(SamplesPath) then
  begin
    if FindFirst(SamplesPath + '\*', FindRec) then
    begin
      try
        repeat
          if (FindRec.Name <> '.') and (FindRec.Name <> '..') then
          begin
            Result := True;
            Break;
          end;
        until not FindNext(FindRec);
      finally
        FindClose(FindRec);
      end;
    end;
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Answer: Integer;
begin
  Result := True;

  // Check on the component selection page, only when samples component is selected
  if (CurPageID = wpSelectComponents) and
     WizardIsComponentSelected('samples') and
     SamplesFolderHasFiles() then
  begin
    Answer := MsgBox(
      'Sample files are already installed in:' + #13#10 +
      ExpandConstant('{commondocs}\RNCSoftware\PTTimeline\Samples') + #13#10#13#10 +
      'Overwrite with the new versions?' + #13#10 +
      '(Any edits you made to the samples will be lost.)',
      mbConfirmation, MB_YESNO);

    if Answer = IDNO then
    begin
      // Deselect the samples component so no files are installed
      // WizardSelectComponents accepts a comma-separated list of components to select;
      // passing only 'main' leaves 'samples' unchecked.
      WizardSelectComponents('main');
    end;
  end;
end;

// ---------------------------------------------------------------------------
// POST-INSTALL sections follow below
// ---------------------------------------------------------------------------

[Run]
; Refresh shell so file associations take effect immediately
Filename: "{cmd}"; Parameters: "/c assoc .pttd=PTTimeline.pttd"; Flags: runhidden
Filename: "{cmd}"; Parameters: "/c assoc .pttp=PTTimeline.pttp"; Flags: runhidden

; Optional: offer to launch PTTEdit after install
Filename: "{app}\pttedit.exe"; Description: "Launch PTTEdit now"; Flags: nowait postinstall skipifsilent unchecked

; Open samples folder after install if samples component was installed
Filename: "{commondocs}\RNCSoftware\PTTimeline\Samples"; Description: "Open sample files folder"; Flags: nowait postinstall skipifsilent shellexec; Components: samples

[UninstallRun]
; Clean up file associations on uninstall
Filename: "{cmd}"; Parameters: "/c assoc .pttd="; Flags: runhidden; RunOnceId: "UnassocPttd"
Filename: "{cmd}"; Parameters: "/c assoc .pttp="; Flags: runhidden; RunOnceId: "UnassocPttp"
