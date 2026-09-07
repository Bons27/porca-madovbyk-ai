Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
batPath = scriptDir & "\Avvia Porca MaDovbyk AI.bat"
shell.Run Chr(34) & batPath & Chr(34), 0, False
