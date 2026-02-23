---
name: feishu-task-manager
description: Manage Feishu (Lark) tasks via API v2. Use when user needs to create, read, update, delete tasks or tasklists, assign tasks to users, set deadlines, check task status, or automate task workflows. Supports task CRUD operations, tasklist management, batch operations, and progress tracking.
---

# Feishu Task Manager

Manage Feishu tasks programmatically using Task API v2.

## Prerequisites

1. **App Credentials**: Need `APP_ID` and `APP_SECRET` from Feishu Open Platform
2. **Permissions**: Application must have `task:task:read` and `task:task:write` permissions
3. **Python SDK**: `lark-oapi` package must be installed

## Quick Start

```python
import lark_oapi as lark
from lark_oapi.api.task.v2 import *

# Initialize client
client = lark.Client.builder() \
    .app_id("cli_xxxxxxxx") \
    .app_secret("xxxxxxxx") \
    .log_level(lark.LogLevel.INFO) \
    .build()
```

## Core Operations

### 1. Task CRUD

#### Create Task
```python
request = CreateTaskRequest.builder() \
    .request_body(CreateTaskRequestBody.builder()
                  .summary("任务标题")
                  .description("任务描述")
                  .assignee("ou_xxxxxxxx")  # 负责人 open_id
                  .due_time("2024-12-31T23:59:59+08:00")
                  .followers(["ou_yyyyyyyy"])  # 关注人
                  .build()) \
    .build()
response = client.task.v2.task.create(request)
```

#### Get Task
```python
request = GetTaskRequest.builder().task_id("task_xxxxxxxx").build()
response = client.task.v2.task.get(request)
```

#### Update Task
```python
request = UpdateTaskRequest.builder() \
    .task_id("task_xxxxxxxx") \
    .request_body(UpdateTaskRequestBody.builder()
                  .summary("新标题")
                  .status("completed")  # todo/in_progress/completed
                  .build()) \
    .build()
response = client.task.v2.task.update(request)
```

#### Delete Task
```python
request = DeleteTaskRequest.builder().task_id("task_xxxxxxxx").build()
response = client.task.v2.task.delete(request)
```

### 2. Query Tasks

#### List Tasks I Created
```python
request = ListTaskRequest.builder()
    .created_by_me(True)
    .page_size(50)
    .build()
response = client.task.v2.task.list(request)
```

#### List Tasks Assigned to Me
```python
request = ListTaskRequest.builder()
    .assigned_to_me(True)
    .page_size(50)
    .build()
response = client.task.v2.task.list(request)
```

#### List Tasks by Status
```python
request = ListTaskRequest.builder()
    .statuses(["todo", "in_progress"])  # 未完成
    .page_size(50)
    .build()
response = client.task.v2.task.list(request)
```

### 3. Tasklist Management

#### Create Tasklist
```python
request = CreateTasklistRequest.builder() \
    .request_body(CreateTasklistRequestBody.builder()
                  .name("项目迭代清单")
                  .description("v2.0 版本任务")
                  .build()) \
    .build()
response = client.task.v2.tasklist.create(request)
tasklist_id = response.data.tasklist_id
```

#### Add Task to Tasklist
```python
request = AddTaskTasklistRequest.builder() \
    .tasklist_id("tasklist_xxxxxxxx") \
    .request_body(AddTaskTasklistRequestBody.builder()
                  .task_id("task_yyyyyyyy")
                  .build()) \
    .build()
response = client.task.v2.tasklist.add_task(request)
```

#### List Tasks in Tasklist
```python
request = ListTaskTasklistRequest.builder() \
    .tasklist_id("tasklist_xxxxxxxx") \
    .page_size(100) \
    .build()
response = client.task.v2.tasklist.list_task(request)
```

#### Get Tasklist Detail
```python
request = GetTasklistRequest.builder().tasklist_id("tasklist_xxxxxxxx").build()
response = client.task.v2.tasklist.get(request)
```

### 4. Batch Operations

#### Complete Multiple Tasks
```python
for task_id in task_ids:
    request = UpdateTaskRequest.builder() \
        .task_id(task_id) \
        .request_body(UpdateTaskRequestBody.builder()
                      .status("completed")
                      .build()) \
        .build()
    client.task.v2.task.update(request)
```

## Advanced Features

### 1. Custom Fields

Tasks support custom fields for extended metadata:

```python
# When creating task with custom fields (via raw API)
request = lark.BaseRequest.builder() \
    .http_method(lark.HttpMethod.POST) \
    .uri("/open-apis/task/v2/tasks") \
    .token_types({lark.AccessTokenType.TENANT}) \
    .body({
        "summary": "任务标题",
        "custom_fields": [
            {"name": "优先级", "value": "高"},
            {"name": "需求类型", "value": "功能开发"}
        ]
    }) \
    .build()
response = client.request(request)
```

### 2. Subtasks

Create subtasks under a parent task:

```python
request = CreateTaskRequest.builder() \
    .request_body(CreateTaskRequestBody.builder()
                  .summary("子任务标题")
                  .parent_task_id("task_parent_xxx")  # 父任务ID
                  .build()) \
    .build()
response = client.task.v2.task.create(request)
```

### 3. Task Comments

```python
# Create comment
request = CreateCommentRequest.builder() \
    .task_id("task_xxxxxxxx") \
    .request_body(CreateCommentRequestBody.builder()
                  .content("这是一条评论")
                  .build()) \
    .build()
response = client.task.v2.comment.create(request)

# List comments
request = ListCommentRequest.builder().task_id("task_xxxxxxxx").build()
response = client.task.v2.comment.list(request)
```

## Automation Workflows

### Daily Standup Report
```python
def generate_daily_report(client, tasklist_id):
    """生成每日任务进展报告"""
    request = ListTaskTasklistRequest.builder() \
        .tasklist_id(tasklist_id) \
        .page_size(100) \
        .build()
    response = client.task.v2.tasklist.list_task(request)
    
    if not response.success():
        return None
    
    tasks = response.data.items
    report = {
        "completed": [t for t in tasks if t.status == "completed"],
        "in_progress": [t for t in tasks if t.status == "in_progress"],
        "todo": [t for t in tasks if t.status == "todo"]
    }
    return report
```

### Auto-Assign Based on Workload
```python
def assign_to_least_loaded(client, assignees, task_title):
    """分配给负载最轻的成员"""
    workloads = {}
    for assignee in assignees:
        request = ListTaskRequest.builder() \
            .assignee(assignee) \
            .statuses(["todo", "in_progress"]) \
            .build()
        response = client.task.v2.task.list(request)
        workloads[assignee] = len(response.data.items) if response.success() else 0
    
    least_loaded = min(workloads, key=workloads.get)
    
    # Create task assigned to least loaded person
    request = CreateTaskRequest.builder() \
        .request_body(CreateTaskRequestBody.builder()
                      .summary(task_title)
                      .assignee(least_loaded)
                      .build()) \
        .build()
    return client.task.v2.task.create(request)
```

## Error Handling

```python
def handle_task_response(response, operation="操作"):
    if not response.success():
        error_msg = f"{operation}失败: {response.code} - {response.msg}"
        if response.code == 99991672:
            error_msg += " (权限不足，请检查应用权限)"
        elif response.code == 99991663:
            error_msg += " (任务不存在)"
        print(error_msg)
        return None
    return response.data
```

## Common Patterns

### Pattern: Create Task with Notification
1. Create task
2. Send IM message to assignee
3. Return task URL

### Pattern: Bulk Import Tasks
1. Parse input (CSV/JSON)
2. Create tasks sequentially
3. Add to tasklist
4. Report creation summary

### Pattern: Recurring Task Setup
1. Create master task
2. Schedule creation of child tasks
3. Set up deadline tracking

## Resources

- **API Reference**: See [references/api-reference.md](references/api-reference.md) for complete API details
- **Helper Scripts**: See [scripts/](scripts/) for reusable Python utilities

## Notes

- Task IDs format: `task_xxxxxxxxxxxxxxxx`
- Tasklist IDs format: `tasklist_xxxxxxxxxxxxxxxx`
- User IDs (open_id) format: `ou_xxxxxxxxxxxxxxxx`
- Time format: RFC 3339 (e.g., `2024-12-31T23:59:59+08:00`)
- Rate limits: Check Feishu documentation for current limits
