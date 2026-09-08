Option Explicit

Dim shell, fso, scriptDir, updaterPath, batPath, updateCode

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
updaterPath = scriptDir & "\Aggiorna Porca MaDovbyk AI.bat"
batPath = scriptDir & "\Avvia Porca MaDovbyk AI.bat"

If Not fso.FileExists(batPath) Then
    MsgBox "Launcher non trovato:" & vbCrLf & batPath, vbCritical, "Porca MaDovbyk AI"
    WScript.Quit 1
End If

' Aggiorna in silenzio quando Git/GitHub Desktop e disponibile.
' Un errore di aggiornamento non impedisce l'avvio della copia locale stabile.
If fso.FileExists(updaterPath) Then
    updateCode = shell.Run(Chr(34) & updaterPath & Chr(34), 0, True)
End If

' 0 = finestra nascosta; False = non bloccare lo script.
shell.Run Chr(34) & batPath & Chr(34), 0, False
