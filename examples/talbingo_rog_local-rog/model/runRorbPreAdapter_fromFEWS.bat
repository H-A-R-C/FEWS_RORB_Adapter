@echo off
setlocal

call %1 
python %2 > %3
call %4

endlocal
