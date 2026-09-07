Option Explicit

Dim shell, fso, scriptDir, batPath

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
batPath = scriptDir & "\Avvia Porca MaDovbyk AI.bat"

If Not fso.FileExists(batPath) Then
    MsgBox "Launcher non trovato:" & vbCrLf & batPath, vbCritical, "Porca MaDovbyk AI"
    WScript.Quit 1
End If

' 0 = finestra nascosta; False = non bloccare lo script.
shell.Run Chr(34) & batPath & Chr(34), 0, False
