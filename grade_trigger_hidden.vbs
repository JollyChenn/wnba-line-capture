' Hidden launcher for grade_trigger.bat - runs it with NO visible console window (style 0)
' and WAITS for it (True) so the task IgnoreNew (no stacking) + 3-min auto-kill apply to whole run.
CreateObject("WScript.Shell").Run "cmd /c ""C:\Users\Axioo\wnba-line-capture\grade_trigger.bat""", 0, True
