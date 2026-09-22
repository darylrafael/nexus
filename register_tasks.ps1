# PowerShell script to register Nexus tasks to wake up and run at 06:59 and 18:59 Mon-Fri

# Define actions
$BriefAction = New-ScheduledTaskAction -Execute "C:\Users\Lenovo\nexus\run_brief.bat"
$ReviewAction = New-ScheduledTaskAction -Execute "C:\Users\Lenovo\nexus\run_review.bat"

# Define triggers (Weekly trigger for Mon-Fri at 6:59 AM and 6:59 PM)
$BriefTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday -At 6:59AM
$ReviewTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday -At 6:59PM

# Define settings: 
# - WakeToRun: Wake laptop up
# - AllowStartIfOnBatteries/DontStopIfGoingOnBatteries: Run even if battery rules apply
# - ExecutionTimeLimit: Force stop task if it takes more than 10 minutes (prevents hanging)
$Settings = New-ScheduledTaskSettingsSet -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

# Register Morning Brief Task
Register-ScheduledTask -TaskName "Nexus_Morning_Brief" -Action $BriefAction -Trigger $BriefTrigger -Settings $Settings -Description "Runs daily brief and wakes laptop if asleep" -Force

# Register Evening Review Task
Register-ScheduledTask -TaskName "Nexus_Evening_Review" -Action $ReviewAction -Trigger $ReviewTrigger -Settings $Settings -Description "Runs evening review and wakes laptop if asleep" -Force

Write-Host "Scheduled tasks updated to 6:59 successfully!"
