#!/usr/bin/env python3
"""
Feishu Task Manager - Python utility for managing Feishu tasks via API v2

Usage:
    python task_manager.py --help
    python task_manager.py list --assigned-to-me
    python task_manager.py create --title "New Task" --assignee ou_xxx
    python task_manager.py complete task_xxx
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

try:
    import lark_oapi as lark
    from lark_oapi.api.task.v2 import *
    from lark_oapi.api.contact.v3 import *
    from lark_oapi.api.im.v1 import *
except ImportError:
    print("Error: lark-oapi not installed. Run: pip install lark-oapi")
    sys.exit(1)


class FeishuTaskManager:
    """Manager for Feishu Task operations"""
    
    def __init__(self, app_id: Optional[str] = None, app_secret: Optional[str] = None):
        """Initialize with app credentials (or from env vars)"""
        self.app_id = app_id or os.getenv("FEISHU_APP_ID")
        self.app_secret = app_secret or os.getenv("FEISHU_APP_SECRET")
        
        if not self.app_id or not self.app_secret:
            raise ValueError(
                "App credentials required. Set FEISHU_APP_ID and FEISHU_APP_SECRET "
                "environment variables or pass to constructor."
            )
        
        self.client = lark.Client.builder() \
            .app_id(self.app_id) \
            .app_secret(self.app_secret) \
            .log_level(lark.LogLevel.WARNING) \
            .build()
    
    def _handle_response(self, response, operation: str = "Operation") -> Optional[Any]:
        """Handle API response and return data or None on error"""
        if not response.success():
            error_msg = f"{operation} failed: {response.code} - {response.msg}"
            if response.code == 99991672:
                error_msg += "\nHint: Check app permissions (task:task:read/write)"
            elif response.code == 99991663:
                error_msg += "\nHint: Task not found, verify task ID"
            print(error_msg, file=sys.stderr)
            return None
        return response.data
    
    # ==================== Task CRUD ====================
    
    def create_task(
        self,
        title: str,
        description: str = "",
        assignee: Optional[str] = None,
        due_time: Optional[str] = None,
        followers: Optional[List[str]] = None,
        parent_task_id: Optional[str] = None
    ) -> Optional[Dict]:
        """Create a new task"""
        body = CreateTaskRequestBody.builder() \
            .summary(title) \
            .description(description)
        
        if assignee:
            body = body.assignee(assignee)
        if due_time:
            body = body.due_time(due_time)
        if followers:
            body = body.followers(followers)
        if parent_task_id:
            body = body.parent_task_id(parent_task_id)
        
        request = CreateTaskRequest.builder() \
            .request_body(body.build()) \
            .build()
        
        response = self.client.task.v2.task.create(request)
        data = self._handle_response(response, "Create task")
        return data.task if data else None
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """Get task details"""
        request = GetTaskRequest.builder().task_id(task_id).build()
        response = self.client.task.v2.task.get(request)
        data = self._handle_response(response, "Get task")
        return data.task if data else None
    
    def update_task(
        self,
        task_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        assignee: Optional[str] = None,
        due_time: Optional[str] = None
    ) -> Optional[Dict]:
        """Update task fields"""
        body = UpdateTaskRequestBody.builder()
        
        if title:
            body = body.summary(title)
        if description:
            body = body.description(description)
        if status:
            body = body.status(status)
        if assignee:
            body = body.assignee(assignee)
        if due_time:
            body = body.due_time(due_time)
        
        request = UpdateTaskRequest.builder() \
            .task_id(task_id) \
            .request_body(body.build()) \
            .build()
        
        response = self.client.task.v2.task.update(request)
        data = self._handle_response(response, "Update task")
        return data.task if data else None
    
    def complete_task(self, task_id: str) -> bool:
        """Mark task as completed"""
        result = self.update_task(task_id, status="completed")
        return result is not None
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task"""
        request = DeleteTaskRequest.builder().task_id(task_id).build()
        response = self.client.task.v2.task.delete(request)
        return response.success()
    
    # ==================== Task Queries ====================
    
    def list_my_tasks(
        self,
        statuses: Optional[List[str]] = None,
        page_size: int = 50
    ) -> List[Dict]:
        """List tasks assigned to me"""
        request = ListTaskRequest.builder() \
            .assigned_to_me(True) \
            .page_size(page_size)
        
        if statuses:
            request = request.statuses(statuses)
        
        response = self.client.task.v2.task.list(request.build())
        data = self._handle_response(response, "List my tasks")
        return data.items if data else []
    
    def list_created_by_me(
        self,
        statuses: Optional[List[str]] = None,
        page_size: int = 50
    ) -> List[Dict]:
        """List tasks created by me"""
        request = ListTaskRequest.builder() \
            .created_by_me(True) \
            .page_size(page_size)
        
        if statuses:
            request = request.statuses(statuses)
        
        response = self.client.task.v2.task.list(request.build())
        data = self._handle_response(response, "List created tasks")
        return data.items if data else []
    
    def list_tasks_by_assignee(
        self,
        assignee: str,
        statuses: Optional[List[str]] = None,
        page_size: int = 50
    ) -> List[Dict]:
        """List tasks by specific assignee"""
        request = ListTaskRequest.builder() \
            .assignee(assignee) \
            .page_size(page_size)
        
        if statuses:
            request = request.statuses(statuses)
        
        response = self.client.task.v2.task.list(request.build())
        data = self._handle_response(response, "List tasks by assignee")
        return data.items if data else []
    
    def get_tasks_due_soon(self, days: int = 3) -> List[Dict]:
        """Get tasks due within specified days"""
        due_before = (datetime.now() + timedelta(days=days)).isoformat()
        
        request = ListTaskRequest.builder() \
            .assigned_to_me(True) \
            .due_before(due_before) \
            .statuses(["todo", "in_progress"]) \
            .page_size(100) \
            .build()
        
        response = self.client.task.v2.task.list(request)
        data = self._handle_response(response, "List tasks due soon")
        return data.items if data else []
    
    # ==================== Tasklist Operations ====================
    
    def create_tasklist(self, name: str, description: str = "") -> Optional[Dict]:
        """Create a new tasklist"""
        request = CreateTasklistRequest.builder() \
            .request_body(
                CreateTasklistRequestBody.builder()
                .name(name)
                .description(description)
                .build()
            ) \
            .build()
        
        response = self.client.task.v2.tasklist.create(request)
        data = self._handle_response(response, "Create tasklist")
        return data.tasklist if data else None
    
    def get_tasklist(self, tasklist_id: str) -> Optional[Dict]:
        """Get tasklist details"""
        request = GetTasklistRequest.builder().tasklist_id(tasklist_id).build()
        response = self.client.task.v2.tasklist.get(request)
        data = self._handle_response(response, "Get tasklist")
        return data.tasklist if data else None
    
    def update_tasklist(
        self,
        tasklist_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[Dict]:
        """Update tasklist"""
        body = UpdateTasklistRequestBody.builder()
        if name:
            body = body.name(name)
        if description:
            body = body.description(description)
        
        request = UpdateTasklistRequest.builder() \
            .tasklist_id(tasklist_id) \
            .request_body(body.build()) \
            .build()
        
        response = self.client.task.v2.tasklist.update(request)
        data = self._handle_response(response, "Update tasklist")
        return data.tasklist if data else None
    
    def delete_tasklist(self, tasklist_id: str) -> bool:
        """Delete a tasklist"""
        request = DeleteTasklistRequest.builder().tasklist_id(tasklist_id).build()
        response = self.client.task.v2.tasklist.delete(request)
        return response.success()
    
    def list_tasklists(self, page_size: int = 50) -> List[Dict]:
        """List all tasklists"""
        # Note: SDK may not expose list tasklists directly, use raw API
        request = lark.BaseRequest.builder() \
            .http_method(lark.HttpMethod.GET) \
            .uri("/open-apis/task/v2/tasklists") \
            .token_types({lark.AccessTokenType.TENANT}) \
            .queries([("page_size", str(page_size))]) \
            .build()
        
        response = self.client.request(request)
        if response.success():
            result = json.loads(str(response.raw.content, lark.UTF_8))
            return result.get("data", {}).get("items", [])
        return []
    
    def add_task_to_tasklist(self, tasklist_id: str, task_id: str) -> bool:
        """Add task to tasklist"""
        request = AddTaskTasklistRequest.builder() \
            .tasklist_id(tasklist_id) \
            .request_body(
                AddTaskTasklistRequestBody.builder()
                .task_id(task_id)
                .build()
            ) \
            .build()
        
        response = self.client.task.v2.tasklist.add_task(request)
        return response.success()
    
    def list_tasks_in_tasklist(
        self,
        tasklist_id: str,
        page_size: int = 100
    ) -> List[Dict]:
        """List all tasks in a tasklist"""
        request = ListTaskTasklistRequest.builder() \
            .tasklist_id(tasklist_id) \
            .page_size(page_size) \
            .build()
        
        response = self.client.task.v2.tasklist.list_task(request)
        data = self._handle_response(response, "List tasks in tasklist")
        return data.items if data else []
    
    # ==================== User Lookup ====================
    
    def get_user_by_email(self, email: str) -> Optional[str]:
        """Get user open_id by email"""
        request = BatchGetIdUserRequest.builder() \
            .user_id_type("open_id") \
            .request_body(
                BatchGetIdUserRequestBody.builder()
                .emails([email])
                .build()
            ) \
            .build()
        
        response = self.client.contact.v3.user.batch_get_id(request)
        if response.success() and response.data:
            users = response.data.user_list
            if users:
                return users[0].user_id
        return None
    
    def get_user_by_phone(self, phone: str) -> Optional[str]:
        """Get user open_id by phone"""
        request = BatchGetIdUserRequest.builder() \
            .user_id_type("open_id") \
            .request_body(
                BatchGetIdUserRequestBody.builder()
                .mobiles([phone])
                .build()
            ) \
            .build()
        
        response = self.client.contact.v3.user.batch_get_id(request)
        if response.success() and response.data:
            users = response.data.user_list
            if users:
                return users[0].user_id
        return None
    
    # ==================== Reporting ====================
    
    def generate_task_report(self, tasklist_id: Optional[str] = None) -> Dict:
        """Generate task status report"""
        if tasklist_id:
            tasks = self.list_tasks_in_tasklist(tasklist_id)
        else:
            tasks = self.list_my_tasks(page_size=100)
        
        report = {
            "total": len(tasks),
            "todo": [],
            "in_progress": [],
            "completed": [],
            "overdue": []
        }
        
        now = datetime.now()
        
        for task in tasks:
            status = task.status
            if status in report:
                report[status].append(task)
            
            # Check overdue
            if task.due_time and status in ["todo", "in_progress"]:
                due = datetime.fromisoformat(task.due_time.replace("Z", "+00:00"))
                if due < now:
                    report["overdue"].append(task)
        
        return report
    
    def print_report(self, report: Dict):
        """Print formatted task report"""
        print(f"\n{'='*50}")
        print(f"Task Report - Total: {report['total']}")
        print(f"{'='*50}")
        print(f"📋 Todo: {len(report['todo'])}")
        print(f"🔄 In Progress: {len(report['in_progress'])}")
        print(f"✅ Completed: {len(report['completed'])}")
        print(f"⚠️  Overdue: {len(report['overdue'])}")
        
        if report['overdue']:
            print(f"\n⚠️  Overdue Tasks:")
            for task in report['overdue']:
                print(f"  - {task.summary} (Due: {task.due_time})")


# ==================== CLI Interface ====================

def main():
    parser = argparse.ArgumentParser(description="Feishu Task Manager")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List tasks")
    list_parser.add_argument("--assigned-to-me", action="store_true", help="Tasks assigned to me")
    list_parser.add_argument("--created-by-me", action="store_true", help="Tasks created by me")
    list_parser.add_argument("--assignee", help="Filter by assignee open_id")
    list_parser.add_argument("--status", choices=["todo", "in_progress", "completed"], action="append")
    list_parser.add_argument("--due-soon", type=int, metavar="DAYS", help="Tasks due within N days")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create a task")
    create_parser.add_argument("--title", required=True, help="Task title")
    create_parser.add_argument("--description", default="", help="Task description")
    create_parser.add_argument("--assignee", help="Assignee open_id")
    create_parser.add_argument("--due", help="Due date (YYYY-MM-DD)")
    create_parser.add_argument("--followers", nargs="+", help="Follower open_ids")
    
    # Get command
    get_parser = subparsers.add_parser("get", help="Get task details")
    get_parser.add_argument("task_id", help="Task ID")
    
    # Update command
    update_parser = subparsers.add_parser("update", help="Update a task")
    update_parser.add_argument("task_id", help="Task ID")
    update_parser.add_argument("--title", help="New title")
    update_parser.add_argument("--description", help="New description")
    update_parser.add_argument("--status", choices=["todo", "in_progress", "completed"])
    update_parser.add_argument("--assignee", help="New assignee")
    update_parser.add_argument("--due", help="New due date (YYYY-MM-DD)")
    
    # Complete command
    complete_parser = subparsers.add_parser("complete", help="Mark task as completed")
    complete_parser.add_argument("task_id", help="Task ID")
    
    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a task")
    delete_parser.add_argument("task_id", help="Task ID")
    
    # Tasklist commands
    tasklist_parser = subparsers.add_parser("tasklist", help="Tasklist operations")
    tasklist_subparsers = tasklist_parser.add_subparsers(dest="tasklist_cmd")
    
    # Create tasklist
    tl_create = tasklist_subparsers.add_parser("create", help="Create tasklist")
    tl_create.add_argument("--name", required=True)
    tl_create.add_argument("--description", default="")
    
    # List tasks in tasklist
    tl_list = tasklist_subparsers.add_parser("list-tasks", help="List tasks in tasklist")
    tl_list.add_argument("tasklist_id", help="Tasklist ID")
    
    # Add task to tasklist
    tl_add = tasklist_subparsers.add_parser("add-task", help="Add task to tasklist")
    tl_add.add_argument("tasklist_id", help="Tasklist ID")
    tl_add.add_argument("task_id", help="Task ID")
    
    # Report command
    report_parser = subparsers.add_parser("report", help="Generate task report")
    report_parser.add_argument("--tasklist", help="Tasklist ID (optional)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize manager
    try:
        manager = FeishuTaskManager()
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Execute command
    if args.command == "list":
        if args.due_soon:
            tasks = manager.get_tasks_due_soon(args.due_soon)
        elif args.created_by_me:
            tasks = manager.list_created_by_me(statuses=args.status)
        elif args.assignee:
            tasks = manager.list_tasks_by_assignee(args.assignee, statuses=args.status)
        else:
            tasks = manager.list_my_tasks(statuses=args.status)
        
        print(f"\nFound {len(tasks)} tasks:")
        for task in tasks:
            status_icon = {"todo": "📋", "in_progress": "🔄", "completed": "✅"}.get(task.status, "❓")
            due = f" (Due: {task.due_time[:10]})" if task.due_time else ""
            print(f"  {status_icon} [{task.task_id}] {task.summary}{due}")
    
    elif args.command == "create":
        due_time = None
        if args.due:
            due_time = f"{args.due}T23:59:59+08:00"
        
        task = manager.create_task(
            title=args.title,
            description=args.description,
            assignee=args.assignee,
            due_time=due_time,
            followers=args.followers
        )
        if task:
            print(f"✅ Task created: {task.task_id}")
            print(f"   URL: {task.url}")
    
    elif args.command == "get":
        task = manager.get_task(args.task_id)
        if task:
            print(f"\nTask: {task.summary}")
            print(f"ID: {task.task_id}")
            print(f"Status: {task.status}")
            print(f"Assignee: {task.assignee}")
            if task.due_time:
                print(f"Due: {task.due_time}")
            if task.description:
                print(f"Description: {task.description}")
            print(f"URL: {task.url}")
    
    elif args.command == "update":
        due_time = None
        if args.due:
            due_time = f"{args.due}T23:59:59+08:00"
        
        task = manager.update_task(
            task_id=args.task_id,
            title=args.title,
            description=args.description,
            status=args.status,
            assignee=args.assignee,
            due_time=due_time
        )
        if task:
            print(f"✅ Task updated: {task.task_id}")
    
    elif args.command == "complete":
        if manager.complete_task(args.task_id):
            print(f"✅ Task {args.task_id} marked as completed")
    
    elif args.command == "delete":
        if manager.delete_task(args.task_id):
            print(f"✅ Task {args.task_id} deleted")
    
    elif args.command == "tasklist":
        if args.tasklist_cmd == "create":
            tasklist = manager.create_tasklist(args.name, args.description)
            if tasklist:
                print(f"✅ Tasklist created: {tasklist.tasklist_id}")
        
        elif args.tasklist_cmd == "list-tasks":
            tasks = manager.list_tasks_in_tasklist(args.tasklist_id)
            print(f"\nFound {len(tasks)} tasks in tasklist:")
            for task in tasks:
                status_icon = {"todo": "📋", "in_progress": "🔄", "completed": "✅"}.get(task.status, "❓")
                print(f"  {status_icon} [{task.task_id}] {task.summary}")
        
        elif args.tasklist_cmd == "add-task":
            if manager.add_task_to_tasklist(args.tasklist_id, args.task_id):
                print(f"✅ Task added to tasklist")
    
    elif args.command == "report":
        report = manager.generate_task_report(args.tasklist)
        manager.print_report(report)


if __name__ == "__main__":
    main()
