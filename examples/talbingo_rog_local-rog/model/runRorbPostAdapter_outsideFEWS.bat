@echo off
setlocal

call d:\FEWS_Applications_svn\SHEWS_trunk_svn\Modules\env_rorb\Scripts\activate.bat
python d:\FEWS_Applications_svn\SHEWS_trunk_svn\Modules\bin_rorb_adapter\post_adapter.py d:\FEWS_Applications_svn\SHEWS_trunk_svn\Modules\rorb\talbingo_p_rog\to_rorb\runinfo.xml
call d:\FEWS_Applications_svn\SHEWS_trunk_svn\Modules\env_rorb\Scripts\deactivate.bat

endlocal  
pause