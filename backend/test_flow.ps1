$task = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/tasks/plan" -Method Post -ContentType "application/json" -Body '{"goal": "find internships"}'
$taskId = $task.task_id
$actionBody = @{
    task_id = $taskId
    action_type = "apply_internship"
    target = "https://example.com/jobs/1"
    payload = @{}
} | ConvertTo-Json
$action = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/actions/queue" -Method Post -ContentType "application/json" -Body $actionBody
$actionId = $action.action_id
$approveBody = @{
    reviewed_by = "tester"
    note = "approved for test"
} | ConvertTo-Json
$resApprove = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/actions/$($actionId)/approve" -Method Post -ContentType "application/json" -Body $approveBody
python -c "from app.services.action_worker import process_next_action; process_next_action()"
$timeline1 = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/tasks/$($taskId)/timeline" -Method Get
$status1 = $timeline1 | Where-Object { $_.action -eq 'action_blocked' }
$consentBody = @{
    action_type = "apply_internship"
    granted_by = "tester"
    expires_at = "2026-12-31T23:59:59+00:00"
} | ConvertTo-Json
$resConsent = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/actions/consents/grant" -Method Post -ContentType "application/json" -Body $consentBody
$action2 = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/actions/queue" -Method Post -ContentType "application/json" -Body $actionBody
$actionId2 = $action2.action_id
$resApprove2 = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/actions/$($actionId2)/approve" -Method Post -ContentType "application/json" -Body $approveBody
python -c "from app.services.action_worker import process_next_action; process_next_action()"
$timeline2 = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/tasks/$($taskId)/timeline" -Method Get
$status2 = $timeline2 | Where-Object { $_.detail -like "*Action #$($actionId2) succeeded*" }
Write-Output "Initial status: $($status1.detail)"
Write-Output "Final status: $($status2.detail)"
