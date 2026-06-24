' Hidden launcher for watchdog_wnba.ps1 - runs it with NO visible window (style 0), waits.
CreateObject("WScript.Shell").Run "powershell -NoProfile -ExecutionPolicy Bypass -File ""C:\Users\Axioo\wnba-line-capture\watchdog_wnba.ps1""", 0, True
