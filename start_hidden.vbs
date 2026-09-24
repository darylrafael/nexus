' Nexus silent launcher — runs run_scheduler.bat with no visible window
Set oShell = CreateObject("WScript.Shell")
projectRoot = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
oShell.Run "cmd /c """ & projectRoot & "\run_scheduler.bat"""", 0, False
