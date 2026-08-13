' Hidden launcher for model_card.py - style 0 = no console window flashing on the desktop.
' Same pattern as run_local.vbs. The 24 argument is the look-ahead window in hours: it must cover
' a slate whose last tip is ~10h out plus the hours between runs, otherwise a late game silently
' drops off the card.
' This script deliberately does NO git. run_local.py's `git pull --rebase --autostash` is what
' twice stashed the working tree, hit a conflict on the pop, and deleted files.
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = "C:\Users\Axioo\wnba-line-capture"
sh.Run "cmd /c python model_card.py 24 >> model_card.log 2>&1", 0, False
