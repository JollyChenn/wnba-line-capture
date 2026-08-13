' Hidden launcher for run_grade.py - the grading suite that used to live only in GitHub Actions.
' Games finish roughly 09:00-12:00 WIB, so this is scheduled to sweep the rest of the day and
' catch late finals. Grading twice is harmless: every script is idempotent on already-graded rows.
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = "C:\Users\Axioo\wnba-line-capture"
sh.Run "cmd /c python run_grade.py >> run_grade.log 2>&1", 0, False
