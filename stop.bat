@echo off

echo Stop DcaTp...


taskkill /FI "WINDOWTITLE eq DcaTp LONG" /T /F

taskkill /FI "WINDOWTITLE eq DcaTp SHORT" /T /F

taskkill /FI "WINDOWTITLE eq DcaTp Backend" /T /F

taskkill /FI "WINDOWTITLE eq DcaTp Frontend" /T /F


echo Done

pause