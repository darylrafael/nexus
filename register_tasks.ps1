# PowerShell script to register Nexus tasks to wake up and run at 06:59 and 18:59 Mon-Fri

# Define actions relative to this repository so clones work anywhere.
$BriefAction = New-ScheduledTaskAction -Execute (Join-Path $PSScriptRoot "run_brief.bat")
$ReviewAction = New-ScheduledTaskAction -Execute (Join-Path $PSScriptRoot "run_review.bat")

# Define triggers (Weekly trigger for Mon-Fri at 6:55 AM and 8:00 PM)
$BriefTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday -At 6:55AM
$ReviewTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday -At 8:00PM

# Define settings: 
# - WakeToRun: Wake laptop up
# - AllowStartIfOnBatteries/DontStopIfGoingOnBatteries: Run even if battery rules apply
# - ExecutionTimeLimit: Force stop task if it takes more than 15 minutes (prevents hanging)
$Settings = New-ScheduledTaskSettingsSet -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 15)

# Register Morning Brief Task
Register-ScheduledTask -TaskName "Nexus_Morning_Brief" -Action $BriefAction -Trigger $BriefTrigger -Settings $Settings -Description "Runs daily brief and wakes laptop if asleep" -Force

# Register Evening Review Task
Register-ScheduledTask -TaskName "Nexus_Evening_Review" -Action $ReviewAction -Trigger $ReviewTrigger -Settings $Settings -Description "Runs evening review and wakes laptop if asleep" -Force

Write-Host "Scheduled tasks aligned with schedule.yaml (06:55 AM & 08:00 PM WIB) successfully!"
