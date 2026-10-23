@echo off
@setlocal
nircmd setcursor 1920 0
nircmd win hide class Shell_TrayWnd

:: This line launches input_monitor.pyw, which simulates the button press that causes the game to
:: exit after a timeout expires with no controller inputs. If you want to keep the game running
:: indefinitely, remove this line and line 26.
for /f %%G in ('powershell -NoProfile -Command "(Start-Process -FilePath 'pythonw.exe' -ArgumentList '%USERPROFILE%\Desktop\Lutero\input_monitor.pyw' -PassThru).Id"') do set PID=%%G

:: Set these variables accordingly.
:: gameName must equal the name of a corresponding image file (without extension)
:: in the digital sign's asset collection, case sensitive.
set "gameName=Game Name"
set "basePath=%USERPROFILE%\Desktop\Lutero"
set "logPath=%USERPROFILE%\Desktop\log.txt"

:: These lines write an exit.bat file in the Lutero directory, which is executed when the game is
:: scheduled to exit by removing the NFC tag or the button is pressed.
(
	echo @echo off
	:: Remove this line if you don't wish to keep logs.
    echo echo %%date%% %%time%% - Stopped ^>^> %logPath%

	:: If you removed the input_monitor.pyw line above, remove this line too.
	echo taskkill /f /pid %PID%
	echo "%basePath%\update.pyw"
	:: Change the argument of taskkill to the game's executable.
	:: Add additional `echo taskkill /f /im` lines if more than one executable is launched.
	echo taskkill /f /im game.exe

	echo del %%~f0
) > "%basePath%\exit.bat"

:: Remove this line if you don't wish to keep logs.
echo %date% %time% - %gameName% >> %logPath%

start /b "" "%basePath%\update.pyw" "%gameName%"

:: wallpaper.pyw takes an optional argument for a specific image file to change the desktop
:: wallpaper to, if you want game-specific images to be shown.
start /b "" "%basePath%\wallpaper.pyw"

:: This line stalls for 2 seconds, so the pre-launch message can be seen. You may wish to remove
:: this line if the game has a naturally long launch time, or increase the number after -n to
:: show the wallpaper image longer. Add 1 to the number of seconds to delay.
ping -n 3 127.0.0.1 >nul

:: Add commands to launch the game below this line.
:: Steam games can be launched with `start steam://rungameid/#######`, using the app ID found in
:: Properties > Updates.
:: For plain executables, you may need to use the form `start /b "" "C:\path\to\game.exe"`.
:: See https://ss64.com/nt/start.html
