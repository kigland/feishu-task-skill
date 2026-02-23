#!/usr/bin/env python3
"""
Task notification utilities for Feishu
- Send reminders for due tasks
- Notify on task status changes
- Daily/weekly digest
"""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional

try:
    import lark_oapi as lark
    from lark_oapi.api.task.v2 import *
    from lark_oapi.api.im.v1 import *
except ImportError:
    print("Error: lark-oapi not installed")
    sys.exit(1)


class TaskNotifier:
    """Send notifications about tasks via Feishu IM"""
    
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
    
    def _send_message(self, receive_id: str, content: Dict, msg_type: str = "interactive") -> bool:
        """Send message to user"""
        try:
            request = CreateMessageRequest.builder() \
                .receive_id_type("open_id") \
                .request_body(
                    CreateMessageRequestBody.builder()
                    .receive_id(receive_id)
                    .msg_type(msg_type)
                    .content(json.dumps(content))
                    .build()
                ) \
                .build()
            
            response = self.client.im.v1.message.create(request)
            return response.success()
        except Exception as e:
            print(f"Failed to send message: {e}")
            return False
    
    def _build_task_card(self, task, title: str, color: str = "blue") -> Dict:
        """Build interactive card for task"""
        status_text = {
            "todo": "📋 待处理",
            "in_progress": "🔄 进行中",
            "completed": "✅ 已完成"
        }.get(task.status, task.status)
        
        due_text = f"\n**截止时间**: {task.due_time[:10]}" if task.due_time else ""
        
        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": color
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**{task.summary}**\n状态: {status_text}{due_text}"
                    }
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "查看任务"},
                            "type": "primary",
                            "url": task.url
                        }
                    ]
                }
            ]
        }
    
    def remind_due_soon(self, assignee: Optional[str] = None, days: int = 1) -> List[str]:
        """Send reminders for tasks due soon"""
        target = assignee or os.getenv("FEISHU_USER_ID")
        if not target:
            print("Error: No assignee specified")
            return []
        
        # Get tasks due soon
        due_before = (datetime.now() + timedelta(days=days)).isoformat()
        request = ListTaskRequest.builder() \
            .assignee(target) \
            .due_before(due_before) \
            .statuses(["todo", "in_progress"]) \
            .page_size(50) \
            .build()
        
        response = self.client.task.v2.task.list(request)
        if not response.success():
            print(f"Error fetching tasks: {response.msg}")
            return []
        
        tasks = response.data.items
        if not tasks:
            return []
        
        # Build notification card
        task_list = "\n".join([
            f"• [{t.status}] {t.summary}" + (f" (Due: {t.due_time[:10]})" if t.due_time else "")
            for t in tasks[:10]  # Limit to 10
        ])
        
        if len(tasks) > 10:
            task_list += f"\n... and {len(tasks) - 10} more"
        
        content = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": f"⏰ 任务提醒 ({days}天内截止)"},
                "template": "orange"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"您有 **{len(tasks)}** 个任务即将截止:\n\n{task_list}"
                    }
                }
            ]
        }
        
        if self._send_message(target, content):
            print(f"✅ Reminder sent to {target} for {len(tasks)} tasks")
            return [t.task_id for t in tasks]
        return []
    
    def notify_task_assigned(
        self,
        task_id: str,
        assignee: str,
        assigner_name: str = ""
    ) -> bool:
        """Notify user when task is assigned to them"""
        # Get task details
        request = GetTaskRequest.builder().task_id(task_id).build()
        response = self.client.task.v2.task.get(request)
        
        if not response.success():
            return False
        
        task = response.data.task
        from_text = f"来自 {assigner_name} 的" if assigner_name else ""
        
        content = self._build_task_card(
            task,
            f"📋 {from_text}新任务分配",
            "blue"
        )
        
        return self._send_message(assignee, content)
    
    def notify_task_completed(
        self,
        task_id: str,
        notify_followers: bool = True
    ) -> bool:
        """Notify followers when task is completed"""
        request = GetTaskRequest.builder().task_id(task_id).build()
        response = self.client.task.v2.task.get(request)
        
        if not response.success():
            return False
        
        task = response.data.task
        
        if not notify_followers or not task.followers:
            return False
        
        content = self._build_task_card(
            task,
            "✅ 任务已完成",
            "green"
        )
        
        success = True
        for follower in task.followers:
            if not self._send_message(follower, content):
                success = False
        
        return success
    
    def send_daily_digest(
        self,
        assignee: Optional[str] = None,
        include_completed: bool = False
    ) -> bool:
        """Send daily task summary"""
        target = assignee or os.getenv("FEISHU_USER_ID")
        if not target:
            print("Error: No assignee specified")
            return False
        
        # Get all tasks
        statuses = ["todo", "in_progress"]
        if include_completed:
            statuses.append("completed")
        
        request = ListTaskRequest.builder() \
            .assignee(target) \
            .statuses(statuses) \
            .page_size(100) \
            .build()
        
        response = self.client.task.v2.task.list(request)
        if not response.success():
            return False
        
        tasks = response.data.items
        
        # Categorize
        todo = [t for t in tasks if t.status == "todo"]
        in_progress = [t for t in tasks if t.status == "in_progress"]
        completed = [t for t in tasks if t.status == "completed"]
        
        # Find overdue
        now = datetime.now()
        overdue = [
            t for t in tasks
            if t.status in ["todo", "in_progress"]
            and t.due_time
            and datetime.fromisoformat(t.due_time.replace("Z", "+00:00")) < now
        ]
        
        content = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": "📊 每日任务摘要"},
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": (
                            f"**📋 待处理**: {len(todo)}\n"
                            f"**🔄 进行中**: {len(in_progress)}\n"
                            f"**✅ 已完成**: {len(completed)}\n"
                            f"**⚠️ 已逾期**: {len(overdue)}"
                        )
                    }
                }
            ]
        }
        
        if overdue:
            overdue_list = "\n".join([f"• {t.summary}" for t in overdue[:5]])
            if len(overdue) > 5:
                overdue_list += f"\n... and {len(overdue) - 5} more"
            
            content["elements"].append({"tag": "hr"})
            content["elements"].append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**⚠️ 逾期任务**:\n{overdue_list}"
                }
            })
        
        return self._send_message(target, content)
    
    def send_weekly_report(
        self,
        assignee: Optional[str] = None,
        tasklist_id: Optional[str] = None
    ) -> bool:
        """Send weekly task report"""
        target = assignee or os.getenv("FEISHU_USER_ID")
        if not target:
            print("Error: No assignee specified")
            return False
        
        # Get tasks from this week
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        
        if tasklist_id:
            request = ListTaskTasklistRequest.builder() \
                .tasklist_id(tasklist_id) \
                .page_size(100) \
                .build()
            response = self.client.task.v2.tasklist.list_task(request)
        else:
            request = ListTaskRequest.builder() \
                .assignee(target) \
                .page_size(100) \
                .build()
            response = self.client.task.v2.task.list(request)
        
        if not response.success():
            return False
        
        tasks = response.data.items
        
        # Filter to this week's activity
        recent_completed = [
            t for t in tasks
            if t.status == "completed"
            and t.completed_time
            and datetime.fromisoformat(t.completed_time.replace("Z", "+00:00")) > datetime.fromisoformat(week_ago)
        ]
        
        recent_created = [
            t for t in tasks
            if datetime.fromisoformat(t.created_time.replace("Z", "+00:00")) > datetime.fromisoformat(week_ago)
        ]
        
        content = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": "📈 本周任务报告"},
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": (
                            f"**本周新建**: {len(recent_created)} 个任务\n"
                            f"**本周完成**: {len(recent_completed)} 个任务\n"
                            f"**总任务数**: {len(tasks)} 个任务"
                        )
                    }
                }
            ]
        }
        
        if recent_completed:
            completed_list = "\n".join([f"✅ {t.summary}" for t in recent_completed[:5]])
            content["elements"].append({"tag": "hr"})
            content["elements"].append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**本周完成任务**:\n{completed_list}"
                }
            })
        
        return self._send_message(target, content)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Feishu Task Notifier")
    subparsers = parser.add_subparsers(dest="command")
    
    # Due soon reminder
    due_soon = subparsers.add_parser("due-soon", help="Send due soon reminder")
    due_soon.add_argument("--assignee", help="Assignee open_id")
    due_soon.add_argument("--days", type=int, default=1, help="Days until due")
    
    # Daily digest
    daily = subparsers.add_parser("daily", help="Send daily digest")
    daily.add_argument("--assignee", help="Assignee open_id")
    daily.add_argument("--include-completed", action="store_true")
    
    # Weekly report
    weekly = subparsers.add_parser("weekly", help="Send weekly report")
    weekly.add_argument("--assignee", help="Assignee open_id")
    weekly.add_argument("--tasklist", help="Tasklist ID")
    
    # Notify assigned
    notify = subparsers.add_parser("notify-assigned", help="Notify task assigned")
    notify.add_argument("--task", required=True, help="Task ID")
    notify.add_argument("--assignee", required=True, help="Assignee open_id")
    notify.add_argument("--assigner", default="", help="Assigner name")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        notifier = TaskNotifier()
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    if args.command == "due-soon":
        notifier.remind_due_soon(args.assignee, args.days)
    
    elif args.command == "daily":
        notifier.send_daily_digest(args.assignee, args.include_completed)
    
    elif args.command == "weekly":
        notifier.send_weekly_report(args.assignee, args.tasklist)
    
    elif args.command == "notify-assigned":
        success = notifier.notify_task_assigned(args.task, args.assignee, args.assigner)
        print(f"Notification {'sent' if success else 'failed'}")
