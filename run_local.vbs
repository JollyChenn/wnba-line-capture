' Hidden launcher for run_local.py - style 0 = no console window flashing on the desktop.
' The bot is meant to be unattended; a popping cmd window every hour is how you end up killing it.
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = "C:\Users\Axioo\wnba-line-capture"
sh.Run "cmd /c python run_local.py >> run_local.log 2>&1", 0, False
