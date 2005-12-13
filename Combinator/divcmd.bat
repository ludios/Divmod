@echo off

python -c "from combinator import sysenv; sysenv.export()" > div_env.bat
call div_env.bat

title Divmod/Win32 Shell
cd ..\..\..
cmd
