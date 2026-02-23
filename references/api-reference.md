# Feishu Task API v2 Reference

Complete API reference for Feishu Task v2 operations.

## Task Operations

### Create Task
**Endpoint**: `POST /open-apis/task/v2/tasks`

**Request Body**:
```json
{
  "summary": "string",           // 任务标题 (required)
  "description": "string",       // 任务描述
  "assignee": "string",          // 负责人 open_id
  "due_time": "string",          // 截止时间 (RFC 3339)
  "followers": ["string"],       // 关注人 open_id 列表
  "parent_task_id": "string",    // 父任务ID (创建子任务)
  "custom_fields": [
    {"name": "string", "value": "string"}
  ]
}
```

**Response**:
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "task": {
      "task_id": "task_xxxxxxxx",
      "summary": "任务标题",
      "description": "任务描述",
      "status": "todo",
      "assignee": "ou_xxxxxxxx",
      "followers": ["ou_yyyyyyyy"],
      "due_time": "2024-12-31T23:59:59+08:00",
      "created_time": "2024-01-01T00:00:00+08:00",
      "updated_time": "2024-01-01T00:00:00+08:00",
      "url": "https://open.feishu.cn/task/xxxx"
    }
  }
}
```

### Get Task
**Endpoint**: `GET /open-apis/task/v2/tasks/:task_id`

**Path Parameters**:
- `task_id`: Task ID

**Response**: Task object (same as Create Task response)

### Update Task
**Endpoint**: `PATCH /open-apis/task/v2/tasks/:task_id`

**Request Body** (all fields optional):
```json
{
  "summary": "string",
  "description": "string",
  "assignee": "string",
  "status": "string",           // todo, in_progress, completed
  "due_time": "string",
  "followers": ["string"],
  "custom_fields": [...]
}
```

### Delete Task
**Endpoint**: `DELETE /open-apis/task/v2/tasks/:task_id`

### List Tasks
**Endpoint**: `GET /open-apis/task/v2/tasks`

**Query Parameters**:
- `created_by_me`: boolean - 我创建的任务
- `assigned_to_me`: boolean - 分配给我的任务
- `followed_by_me`: boolean - 我关注的任务
- `statuses`: string[] - 状态过滤 (todo, in_progress, completed)
- `assignee`: string - 指定负责人
- `due_before`: string - 截止时间在指定时间之前
- `due_after`: string - 截止时间在指定时间之后
- `page_size`: integer (default 50, max 100)
- `page_token`: string - 分页令牌

**Response**:
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "items": [...],
    "page_token": "string",
    "has_more": false
  }
}
```

## Tasklist Operations

### Create Tasklist
**Endpoint**: `POST /open-apis/task/v2/tasklists`

**Request Body**:
```json
{
  "name": "string",              // 清单名称 (required)
  "description": "string"        // 清单描述
}
```

**Response**:
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "tasklist": {
      "tasklist_id": "tasklist_xxxxxxxx",
      "name": "清单名称",
      "description": "描述",
      "created_time": "2024-01-01T00:00:00+08:00",
      "updated_time": "2024-01-01T00:00:00+08:00"
    }
  }
}
```

### Get Tasklist
**Endpoint**: `GET /open-apis/task/v2/tasklists/:tasklist_id`

### Update Tasklist
**Endpoint**: `PATCH /open-apis/task/v2/tasklists/:tasklist_id`

**Request Body**:
```json
{
  "name": "string",
  "description": "string"
}
```

### Delete Tasklist
**Endpoint**: `DELETE /open-apis/task/v2/tasklists/:tasklist_id`

### List Tasks in Tasklist
**Endpoint**: `GET /open-apis/task/v2/tasklists/:tasklist_id/tasks`

**Query Parameters**:
- `page_size`: integer
- `page_token`: string

### Add Task to Tasklist
**Endpoint**: `POST /open-apis/task/v2/tasklists/:tasklist_id/tasks`

**Request Body**:
```json
{
  "task_id": "string"            // 任务ID (required)
}
```

### Remove Task from Tasklist
**Endpoint**: `DELETE /open-apis/task/v2/tasklists/:tasklist_id/tasks/:task_id`

## Comment Operations

### Create Comment
**Endpoint**: `POST /open-apis/task/v2/tasks/:task_id/comments`

**Request Body**:
```json
{
  "content": "string"             // 评论内容 (required)
}
```

### List Comments
**Endpoint**: `GET /open-apis/task/v2/tasks/:task_id/comments`

**Query Parameters**:
- `page_size`: integer
- `page_token`: string

### Delete Comment
**Endpoint**: `DELETE /open-apis/task/v2/tasks/:task_id/comments/:comment_id`

## Task Status Values

| Status | Description |
|--------|-------------|
| `todo` | 待处理 |
| `in_progress` | 进行中 |
| `completed` | 已完成 |

## Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| 0 | Success | - |
| 99991672 | Permission denied | Check app permissions in console |
| 99991663 | Task not found | Verify task_id exists |
| 99991664 | Tasklist not found | Verify tasklist_id exists |
| 99991665 | User not found | Verify open_id is correct |
| 99991666 | Invalid parameter | Check request body format |
| 99991667 | Rate limit exceeded | Reduce request frequency |

## Data Types

### Task Object
```json
{
  "task_id": "string",
  "summary": "string",
  "description": "string",
  "status": "string",
  "assignee": "string",
  "followers": ["string"],
  "due_time": "string",
  "created_time": "string",
  "updated_time": "string",
  "completed_time": "string",
  "parent_task_id": "string",
  "custom_fields": [CustomField],
  "url": "string"
}
```

### Tasklist Object
```json
{
  "tasklist_id": "string",
  "name": "string",
  "description": "string",
  "created_time": "string",
  "updated_time": "string",
  "owner": "string"
}
```

### Comment Object
```json
{
  "comment_id": "string",
  "content": "string",
  "creator": "string",
  "created_time": "string"
}
```

### CustomField Object
```json
{
  "name": "string",
  "value": "string",
  "type": "string"
}
```

## Python SDK Types

### Import Path
```python
from lark_oapi.api.task.v2 import *
```

### Key Classes
- `CreateTaskRequest`, `CreateTaskRequestBody`, `CreateTaskResponse`
- `GetTaskRequest`, `GetTaskResponse`
- `UpdateTaskRequest`, `UpdateTaskRequestBody`, `UpdateTaskResponse`
- `DeleteTaskRequest`, `DeleteTaskResponse`
- `ListTaskRequest`, `ListTaskResponse`
- `CreateTasklistRequest`, `CreateTasklistRequestBody`, `CreateTasklistResponse`
- `GetTasklistRequest`, `GetTasklistResponse`
- `UpdateTasklistRequest`, `UpdateTasklistRequestBody`, `UpdateTasklistResponse`
- `DeleteTasklistRequest`, `DeleteTasklistResponse`
- `ListTaskTasklistRequest`, `ListTaskTasklistResponse`
- `AddTaskTasklistRequest`, `AddTaskTasklistRequestBody`, `AddTaskTasklistResponse`
- `CreateCommentRequest`, `CreateCommentRequestBody`, `CreateCommentResponse`
- `ListCommentRequest`, `ListCommentResponse`
