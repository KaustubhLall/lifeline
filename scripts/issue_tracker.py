#!/usr/bin/env python3
"""
LifeLine Issue Tracking and Progress Monitoring Script

This script provides automated tracking and reporting for the LifeLine project issues.
It can be used to generate progress reports, update issue status, and monitor metrics.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any
import argparse

# Issue data structure
ISSUES = {
    "critical": [
        {"id": 42, "title": "Fix middleware order - APICSRFExemptMiddleware", "type": "Security", "component": "Backend", "effort": 1, "status": "Open"},
        {"id": 14, "title": "Secure ALLOWED_HOSTS for production", "type": "Security", "component": "Infrastructure", "effort": 2, "status": "Open"},
        {"id": 10, "title": "Improve production secret key security", "type": "Security", "component": "Infrastructure", "effort": 1, "status": "Open"},
    ],
    "high": [],
    "medium": [
        {"id": 51, "title": "Fix inconsistent MIME construction in gmail_mcp.py", "type": "Bug", "component": "Integrations", "effort": 3, "status": "Open"},
        {"id": 43, "title": "Standardize CORS configuration", "type": "Configuration", "component": "Infrastructure", "effort": 2, "status": "Open"},
        {"id": 13, "title": "Pin numpy dependency version", "type": "Configuration", "component": "Infrastructure", "effort": 1, "status": "Open"},
        {"id": 11, "title": "Replace threading with proper background task queue", "type": "Performance", "component": "Backend", "effort": 8, "status": "Open"},
        {"id": 9, "title": "Optimize memory search with vector database", "type": "Performance", "component": "Backend", "effort": 16, "status": "Open"},
    ],
    "low": [
        {"id": 50, "title": "Remove duplicate imports in gmail_mcp.py", "type": "Cleanup", "component": "Integrations", "effort": 0.5, "status": "Open"},
        {"id": 44, "title": "Remove redundant logic in APICSRFExemptMiddleware", "type": "Cleanup", "component": "Backend", "effort": 1, "status": "Open"},
        {"id": 12, "title": "Remove unused asyncio import", "type": "Cleanup", "component": "Backend", "effort": 0.5, "status": "Open"},
    ]
}

class IssueTracker:
    def __init__(self):
        self.issues = ISSUES
        self.status_file = "issue_status.json"
        self.load_status()
    
    def load_status(self):
        """Load issue status from file if it exists"""
        if os.path.exists(self.status_file):
            try:
                with open(self.status_file, 'r') as f:
                    status_data = json.load(f)
                    # Update status from saved data
                    for priority in self.issues:
                        for issue in self.issues[priority]:
                            issue_id = str(issue["id"])
                            if issue_id in status_data:
                                issue.update(status_data[issue_id])
            except json.JSONDecodeError:
                print("Warning: Could not load status file")
    
    def save_status(self):
        """Save current issue status to file"""
        status_data = {}
        for priority in self.issues:
            for issue in self.issues[priority]:
                status_data[str(issue["id"])] = {
                    "status": issue["status"],
                    "assignee": issue.get("assignee", ""),
                    "last_updated": datetime.now().isoformat()
                }
        
        with open(self.status_file, 'w') as f:
            json.dump(status_data, f, indent=2)
    
    def get_all_issues(self) -> List[Dict[str, Any]]:
        """Get all issues in a flat list"""
        all_issues = []
        for priority in self.issues:
            for issue in self.issues[priority]:
                issue["priority"] = priority
                all_issues.append(issue)
        return all_issues
    
    def update_issue_status(self, issue_id: int, status: str, assignee: str = ""):
        """Update the status of a specific issue"""
        for priority in self.issues:
            for issue in self.issues[priority]:
                if issue["id"] == issue_id:
                    issue["status"] = status
                    if assignee:
                        issue["assignee"] = assignee
                    self.save_status()
                    return True
        return False
    
    def generate_progress_report(self) -> str:
        """Generate a comprehensive progress report"""
        all_issues = self.get_all_issues()
        
        # Calculate metrics
        total_issues = len(all_issues)
        completed = len([i for i in all_issues if i["status"] == "Completed"])
        in_progress = len([i for i in all_issues if i["status"] == "In Progress"])
        open_issues = len([i for i in all_issues if i["status"] == "Open"])
        
        total_effort = sum(i["effort"] for i in all_issues)
        completed_effort = sum(i["effort"] for i in all_issues if i["status"] == "Completed")
        
        # Generate report
        report = f"""
# LifeLine Project Progress Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary Metrics
- **Total Issues**: {total_issues}
- **Completed**: {completed} ({completed/total_issues*100:.1f}%)
- **In Progress**: {in_progress} ({in_progress/total_issues*100:.1f}%)
- **Open**: {open_issues} ({open_issues/total_issues*100:.1f}%)

## Effort Metrics
- **Total Effort**: {total_effort} hours
- **Completed Effort**: {completed_effort} hours ({completed_effort/total_effort*100:.1f}%)
- **Remaining Effort**: {total_effort - completed_effort} hours

## Issues by Priority

"""
        
        for priority in ["critical", "high", "medium", "low"]:
            priority_issues = self.issues[priority]
            if not priority_issues:
                continue
                
            priority_emoji = {"critical": "🔴", "high": "🟡", "medium": "🟠", "low": "🟢"}
            report += f"### {priority_emoji[priority]} {priority.title()} Priority ({len(priority_issues)} issues)\n\n"
            
            for issue in priority_issues:
                status_emoji = {"Open": "⏳", "In Progress": "🔄", "Ready for Review": "👀", "Completed": "✅"}
                report += f"- {status_emoji.get(issue['status'], '❓')} **#{issue['id']}**: {issue['title']}\n"
                report += f"  - Status: {issue['status']}\n"
                report += f"  - Effort: {issue['effort']}h\n"
                if issue.get('assignee'):
                    report += f"  - Assignee: {issue['assignee']}\n"
                report += "\n"
        
        return report
    
    def generate_sprint_plan(self, sprint_capacity: int = 40) -> str:
        """Generate a sprint plan based on priority and capacity"""
        all_issues = [i for i in self.get_all_issues() if i["status"] == "Open"]
        all_issues.sort(key=lambda x: (x["priority"] != "critical", x["priority"] != "high", x["effort"]))
        
        sprint_issues = []
        current_capacity = 0
        
        for issue in all_issues:
            if current_capacity + issue["effort"] <= sprint_capacity:
                sprint_issues.append(issue)
                current_capacity += issue["effort"]
            else:
                break
        
        plan = f"""
# Sprint Plan (Capacity: {sprint_capacity}h)
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Selected Issues ({current_capacity}h / {sprint_capacity}h capacity)

"""
        
        for issue in sprint_issues:
            priority_emoji = {"critical": "🔴", "high": "🟡", "medium": "🟠", "low": "🟢"}
            plan += f"- {priority_emoji[issue['priority']]} **#{issue['id']}**: {issue['title']} ({issue['effort']}h)\n"
        
        remaining_capacity = sprint_capacity - current_capacity
        if remaining_capacity > 0:
            plan += f"\n## Remaining Capacity: {remaining_capacity}h\n"
            plan += "Consider taking on additional low-effort items or planning next sprint.\n"
        
        return plan

def main():
    parser = argparse.ArgumentParser(description="LifeLine Issue Tracking Tool")
    parser.add_argument("command", choices=["report", "sprint", "update", "list"], 
                       help="Command to execute")
    parser.add_argument("--issue-id", type=int, help="Issue ID for update command")
    parser.add_argument("--status", help="New status for issue")
    parser.add_argument("--assignee", help="Assignee for issue")
    parser.add_argument("--capacity", type=int, default=40, help="Sprint capacity in hours")
    parser.add_argument("--output", help="Output file for reports")
    
    args = parser.parse_args()
    
    tracker = IssueTracker()
    
    if args.command == "report":
        report = tracker.generate_progress_report()
        if args.output:
            with open(args.output, 'w') as f:
                f.write(report)
            print(f"Report saved to {args.output}")
        else:
            print(report)
    
    elif args.command == "sprint":
        plan = tracker.generate_sprint_plan(args.capacity)
        if args.output:
            with open(args.output, 'w') as f:
                f.write(plan)
            print(f"Sprint plan saved to {args.output}")
        else:
            print(plan)
    
    elif args.command == "update":
        if not args.issue_id or not args.status:
            print("Error: --issue-id and --status are required for update command")
            sys.exit(1)
        
        success = tracker.update_issue_status(args.issue_id, args.status, args.assignee or "")
        if success:
            print(f"Updated issue #{args.issue_id} to status: {args.status}")
        else:
            print(f"Error: Issue #{args.issue_id} not found")
    
    elif args.command == "list":
        all_issues = tracker.get_all_issues()
        print("All Issues:")
        for issue in all_issues:
            priority_emoji = {"critical": "🔴", "high": "🟡", "medium": "🟠", "low": "🟢"}
            print(f"{priority_emoji[issue['priority']]} #{issue['id']}: {issue['title']} ({issue['status']})")

if __name__ == "__main__":
    main()