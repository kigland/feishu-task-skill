#!/usr/bin/env python3
"""
Bulk operations for Feishu tasks
- Import tasks from CSV/JSON
- Bulk assign tasks
- Bulk update status
- Bulk delete
"""

import os
import sys
import json
import csv
import time
from typing import List, Dict, Optional
from datetime import datetime

try:
    import lark_oapi as lark
    from lark_oapi.api.task.v2 import *
except ImportError:
    print("Error: lark-oapi not installed. Run: pip install lark-oapi")
    sys.exit(1)


class BulkTaskOperations:
    """Bulk operations for Feishu tasks"""
    
    def __init__(self, app_id: Optional[str] = None, app_secret: Optional[str] = None):
        self.app_id = app_id or os.getenv("FEISHU_APP_ID")
        self.app_secret = app_secret or os.getenv("FEISHU_APP_SECRET")
        
        if not self.app_id or not self.app_secret:
            raise ValueError("App credentials required")
        
        self.client = lark.Client.builder() \
            .app_id(self.app_id) \
            .app_secret(self.app_secret) \
            .log_level(lark.LogLevel.WARNING) \
            .build()
    
    def import_from_csv(
        self,
        csv_path: str,
        tasklist_id: Optional[str] = None,
        default_assignee: Optional[str] = None
    ) -> Dict[str, List]:
        """Import tasks from CSV file
        
        CSV format:
        title,description,assignee,due_date,status
        Task 1,Desc 1,ou_xxx,2024-12-31,todo
        Task 2,Desc 2,ou_yyy,2024-12-31,in_progress
        """
        results = {"created": [], "failed": []}
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    # Build request
                    body = CreateTaskRequestBody.builder() \
                        .summary(row.get("title", "Untitled"))
                    
                    if row.get("description"):
                        body = body.description(row["description"])
                    
                    assignee = row.get("assignee") or default_assignee
                    if assignee:
                        body = body.assignee(assignee)
                    
                    if row.get("due_date"):
                        due_time = f"{row['due_date']}T23:59:59+08:00"
                        body = body.due_time(due_time)
                    
                    request = CreateTaskRequest.builder() \
                        .request_body(body.build()) \
                        .build()
                    
                    response = self.client.task.v2.task.create(request)
                    
                    if response.success():
                        task = response.data.task
                        results["created"].append(task)
                        
                        # Add to tasklist if specified
                        if tasklist_id:
                            self._add_to_tasklist(tasklist_id, task.task_id)
                        
                        print(f"✅ Created: {task.summary} ({task.task_id})")
                    else:
                        results["failed"].append({
                            "row": row,
                            "error": f"{response.code}: {response.msg}"
                        })
                        print(f"❌ Failed: {row.get('title')} - {response.msg}")
                    
                    # Rate limiting
                    time.sleep(0.2)
                    
                except Exception as e:
                    results["failed"].append({"row": row, "error": str(e)})
                    print(f"❌ Error: {row.get('title')} - {e}")
        
        return results
    
    def import_from_json(
        self,
        json_path: str,
        tasklist_id: Optional[str] = None
    ) -> Dict[str, List]:
        """Import tasks from JSON file
        
        JSON format:
        [
          {
            "title": "Task 1",
            "description": "Desc 1",
            "assignee": "ou_xxx",
            "due_time": "2024-12-31T23:59:59+08:00",
            "status": "todo"
          }
        ]
        """
        results = {"created": [], "failed": []}
        
        with open(json_path, 'r', encoding='utf-8') as f:
            tasks = json.load(f)
        
        for task_data in tasks:
            try:
                body = CreateTaskRequestBody.builder() \
                    .summary(task_data.get("title", "Untitled"))
                
                if task_data.get("description"):
                    body = body.description(task_data["description"])
                if task_data.get("assignee"):
                    body = body.assignee(task_data["assignee"])
                if task_data.get("due_time"):
                    body = body.due_time(task_data["due_time"])
                
                request = CreateTaskRequest.builder() \
                    .request_body(body.build()) \
                    .build()
                
                response = self.client.task.v2.task.create(request)
                
                if response.success():
                    task = response.data.task
                    results["created"].append(task)
                    
                    if tasklist_id:
                        self._add_to_tasklist(tasklist_id, task.task_id)
                    
                    print(f"✅ Created: {task.summary}")
                else:
                    results["failed"].append({
                        "data": task_data,
                        "error": f"{response.code}: {response.msg}"
                    })
                    print(f"❌ Failed: {task_data.get('title')}")
                
                time.sleep(0.2)
                
            except Exception as e:
                results["failed"].append({"data": task_data, "error": str(e)})
                print(f"❌ Error: {task_data.get('title')} - {e}")
        
        return results
    
    def bulk_assign(
        self,
        task_ids: List[str],
        assignee: str,
        delay: float = 0.2
    ) -> Dict[str, List]:
        """Bulk assign tasks to a user"""
        results = {"updated": [], "failed": []}
        
        for task_id in task_ids:
            try:
                request = UpdateTaskRequest.builder() \
                    .task_id(task_id) \
                    .request_body(
                        UpdateTaskRequestBody.builder()
                        .assignee(assignee)
                        .build()
                    ) \
                    .build()
                
                response = self.client.task.v2.task.update(request)
                
                if response.success():
                    results["updated"].append(task_id)
                    print(f"✅ Assigned: {task_id}")
                else:
                    results["failed"].append({
                        "task_id": task_id,
                        "error": f"{response.code}: {response.msg}"
                    })
                    print(f"❌ Failed: {task_id} - {response.msg}")
                
                time.sleep(delay)
                
            except Exception as e:
                results["failed"].append({"task_id": task_id, "error": str(e)})
                print(f"❌ Error: {task_id} - {e}")
        
        return results
    
    def bulk_update_status(
        self,
        task_ids: List[str],
        status: str,
        delay: float = 0.2
    ) -> Dict[str, List]:
        """Bulk update task status"""
        results = {"updated": [], "failed": []}
        
        for task_id in task_ids:
            try:
                request = UpdateTaskRequest.builder() \
                    .task_id(task_id) \
                    .request_body(
                        UpdateTaskRequestBody.builder()
                        .status(status)
                        .build()
                    ) \
                    .build()
                
                response = self.client.task.v2.task.update(request)
                
                if response.success():
                    results["updated"].append(task_id)
                    print(f"✅ Updated: {task_id} -> {status}")
                else:
                    results["failed"].append({
                        "task_id": task_id,
                        "error": f"{response.code}: {response.msg}"
                    })
                    print(f"❌ Failed: {task_id}")
                
                time.sleep(delay)
                
            except Exception as e:
                results["failed"].append({"task_id": task_id, "error": str(e)})
        
        return results
    
    def bulk_set_due_date(
        self,
        task_ids: List[str],
        due_date: str,
        delay: float = 0.2
    ) -> Dict[str, List]:
        """Bulk set due date for tasks"""
        results = {"updated": [], "failed": []}
        due_time = f"{due_date}T23:59:59+08:00"
        
        for task_id in task_ids:
            try:
                request = UpdateTaskRequest.builder() \
                    .task_id(task_id) \
                    .request_body(
                        UpdateTaskRequestBody.builder()
                        .due_time(due_time)
                        .build()
                    ) \
                    .build()
                
                response = self.client.task.v2.task.update(request)
                
                if response.success():
                    results["updated"].append(task_id)
                    print(f"✅ Updated due date: {task_id}")
                else:
                    results["failed"].append({
                        "task_id": task_id,
                        "error": f"{response.code}: {response.msg}"
                    })
                    print(f"❌ Failed: {task_id}")
                
                time.sleep(delay)
                
            except Exception as e:
                results["failed"].append({"task_id": task_id, "error": str(e)})
        
        return results
    
    def bulk_delete(
        self,
        task_ids: List[str],
        delay: float = 0.2
    ) -> Dict[str, List]:
        """Bulk delete tasks"""
        results = {"deleted": [], "failed": []}
        
        for task_id in task_ids:
            try:
                request = DeleteTaskRequest.builder().task_id(task_id).build()
                response = self.client.task.v2.task.delete(request)
                
                if response.success():
                    results["deleted"].append(task_id)
                    print(f"✅ Deleted: {task_id}")
                else:
                    results["failed"].append({
                        "task_id": task_id,
                        "error": f"{response.code}: {response.msg}"
                    })
                    print(f"❌ Failed: {task_id}")
                
                time.sleep(delay)
                
            except Exception as e:
                results["failed"].append({"task_id": task_id, "error": str(e)})
        
        return results
    
    def export_to_csv(
        self,
        tasklist_id: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> str:
        """Export tasks to CSV"""
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"tasks_export_{timestamp}.csv"
        
        # Get tasks
        if tasklist_id:
            request = ListTaskTasklistRequest.builder() \
                .tasklist_id(tasklist_id) \
                .page_size(100) \
                .build()
            response = self.client.task.v2.tasklist.list_task(request)
        else:
            request = ListTaskRequest.builder() \
                .assigned_to_me(True) \
                .page_size(100) \
                .build()
            response = self.client.task.v2.task.list(request)
        
        if not response.success():
            print(f"Error: {response.code} - {response.msg}")
            return ""
        
        tasks = response.data.items
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "task_id", "summary", "description", "status",
                "assignee", "due_time", "created_time", "url"
            ])
            
            for task in tasks:
                writer.writerow([
                    task.task_id,
                    task.summary,
                    task.description or "",
                    task.status,
                    task.assignee or "",
                    task.due_time or "",
                    task.created_time,
                    task.url
                ])
        
        print(f"✅ Exported {len(tasks)} tasks to {output_path}")
        return output_path
    
    def _add_to_tasklist(self, tasklist_id: str, task_id: str):
        """Helper to add task to tasklist"""
        try:
            request = AddTaskTasklistRequest.builder() \
                .tasklist_id(tasklist_id) \
                .request_body(
                    AddTaskTasklistRequestBody.builder()
                    .task_id(task_id)
                    .build()
                ) \
                .build()
            self.client.task.v2.tasklist.add_task(request)
        except:
            pass


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Bulk Feishu Task Operations")
    subparsers = parser.add_subparsers(dest="command")
    
    # Import CSV
    import_csv = subparsers.add_parser("import-csv", help="Import from CSV")
    import_csv.add_argument("--file", required=True, help="CSV file path")
    import_csv.add_argument("--tasklist", help="Add to tasklist")
    import_csv.add_argument("--default-assignee", help="Default assignee")
    
    # Import JSON
    import_json = subparsers.add_parser("import-json", help="Import from JSON")
    import_json.add_argument("--file", required=True, help="JSON file path")
    import_json.add_argument("--tasklist", help="Add to tasklist")
    
    # Bulk assign
    bulk_assign = subparsers.add_parser("bulk-assign", help="Bulk assign tasks")
    bulk_assign.add_argument("--tasks", required=True, nargs="+", help="Task IDs")
    bulk_assign.add_argument("--assignee", required=True, help="Assignee open_id")
    
    # Bulk status
    bulk_status = subparsers.add_parser("bulk-status", help="Bulk update status")
    bulk_status.add_argument("--tasks", required=True, nargs="+", help="Task IDs")
    bulk_status.add_argument("--status", required=True, choices=["todo", "in_progress", "completed"])
    
    # Bulk due date
    bulk_due = subparsers.add_parser("bulk-due", help="Bulk set due date")
    bulk_due.add_argument("--tasks", required=True, nargs="+", help="Task IDs")
    bulk_due.add_argument("--date", required=True, help="Due date (YYYY-MM-DD)")
    
    # Bulk delete
    bulk_delete = subparsers.add_parser("bulk-delete", help="Bulk delete tasks")
    bulk_delete.add_argument("--tasks", required=True, nargs="+", help="Task IDs")
    
    # Export
    export = subparsers.add_parser("export", help="Export tasks to CSV")
    export.add_argument("--tasklist", help="Tasklist ID (optional)")
    export.add_argument("--output", help="Output file path")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        ops = BulkTaskOperations()
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    if args.command == "import-csv":
        results = ops.import_from_csv(args.file, args.tasklist, args.default_assignee)
        print(f"\nSummary: {len(results['created'])} created, {len(results['failed'])} failed")
    
    elif args.command == "import-json":
        results = ops.import_from_json(args.file, args.tasklist)
        print(f"\nSummary: {len(results['created'])} created, {len(results['failed'])} failed")
    
    elif args.command == "bulk-assign":
        results = ops.bulk_assign(args.tasks, args.assignee)
        print(f"\nSummary: {len(results['updated'])} updated, {len(results['failed'])} failed")
    
    elif args.command == "bulk-status":
        results = ops.bulk_update_status(args.tasks, args.status)
        print(f"\nSummary: {len(results['updated'])} updated, {len(results['failed'])} failed")
    
    elif args.command == "bulk-due":
        results = ops.bulk_set_due_date(args.tasks, args.date)
        print(f"\nSummary: {len(results['updated'])} updated, {len(results['failed'])} failed")
    
    elif args.command == "bulk-delete":
        results = ops.bulk_delete(args.tasks)
        print(f"\nSummary: {len(results['deleted'])} deleted, {len(results['failed'])} failed")
    
    elif args.command == "export":
        ops.export_to_csv(args.tasklist, args.output)
