' Nexus silent launcher — runs run_scheduler.bat with no visible window
Set oShell = CreateObject("WScript.Shell")
oShell.Run "cmd /c C:\Users\Lenovo\nexus\run_scheduler.bat", 0, False
