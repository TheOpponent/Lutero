@echo off
@setlocal
nircmd setcursor 1920 0

:: Set these variables accordingly.
:: gameName must equal the name of a corresponding image file (without extension) 
:: in the digital sign's asset collection, case sensitive.
set "gameName=Game Name"
set "basePath=%USERPROFILE%\Desktop\bat"
set "logPath=%USERPROFILE%\Desktop\log.txt"
set "exitPath=%basePath%\exit.bat"
(
	echo @echo off
	:: Remove this line if you don't wish to keep logs.
    echo echo %%date%% %%time%% - Stopped ^>^> %logPath%
	
	echo nircmd exec hide python "%basePath%\update.py"
	:: Change the argument of taskkill to the image name of the executable of the game.
	:: Add additional `echo taskkill /f /im` lines if more than one executable is launched.
	echo taskkill /f /im game.exe
	::
	echo del %%~f0
) > %exitPath%

:: Remove this line if you don't wish to keep logs.
echo %date% %time% - %gameName% >> %logPath%

nircmd exec hide python "%basePath%\update.py" "%gameName%"
nircmd exec hide python "%basePath%\wallpaper.py"
:: You may wish to remove this timeout line if the game has a naturally long launch time.
timeout /t 2 
nircmd win hide class Shell_TrayWnd

:: Add commands to launch the game below this line.

