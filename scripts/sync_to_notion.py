#!/usr/bin/env python3
"""
Notion Knowledge Base Sync
Syncs all documents from the inventory to Notion knowledge base.
"""

import os
import json
import requests
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

class NotionSync:
    def __init__(self, notion_api_key: str, database_id: str):
        self.api_key = notion_api_key
        self.database_id = database_id
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
    
    def read_file_content(self, file_path: str) -> str:
        """Read file content."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"⚠️  Error reading {file_path}: {e}")
            return ""
    
    def create_page(self, doc_info: Dict, content: str) -> Optional[str]:
        """Create a Notion page for a document."""
        # Create page properties
        properties = {
            "Name": {
                "title": [{"text": {"content": doc_info["name"]}}]
            },
            "Path": {
                "rich_text": [{"text": {"content": doc_info["path"]}}]
            },
            "Category": {
                "select": {"name": doc_info["category"]}
            },
            "Size": {
                "number": doc_info["size_bytes"]
            },
            "Modified": {
                "date": {"start": doc_info["modified"]}
            },
            "GitHub": {
                "url": doc_info["url_github"] if doc_info["url_github"] else None
            },
            "Local Path": {
                "rich_text": [{"text": {"content": doc_info["absolute_path"]}}]
            },
            "Hash": {
                "rich_text": [{"text": {"content": doc_info["hash"]}}]
            }
        }
        
        # Create page with content
        page_data = {
            "parent": {"database_id": self.database_id},
            "properties": properties,
            "children": [
                {
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": [{"text": {"content": doc_info["name"]}}]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {"text": {"content": f"Path: {doc_info['path']}\n"}},
                            {"text": {"content": f"Category: {doc_info['category']}\n"}},
                            {"text": {"content": f"Size: {doc_info['size_bytes']:,} bytes\n"}},
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "divider",
                    "divider": {}
                },
                {
                    "object": "block",
                    "type": "code",
                    "code": {
                        "language": "markdown",
                        "rich_text": [{"text": {"content": content}}]
                    }
                }
            ]
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/pages",
                headers=self.headers,
                json=page_data
            )
            response.raise_for_status()
            page_id = response.json()["id"]
            print(f"✓ Created Notion page for {doc_info['name']}")
            return page_id
        except Exception as e:
            print(f"⚠️  Error creating page for {doc_info['name']}: {e}")
            return None
    
    def update_page(self, page_id: str, doc_info: Dict, content: str):
        """Update an existing Notion page."""
        # Update properties
        properties = {
            "Modified": {
                "date": {"start": doc_info["modified"]}
            },
            "Hash": {
                "rich_text": [{"text": {"content": doc_info["hash"]}}]
            }
        }
        
        try:
            # Update properties
            requests.patch(
                f"{self.base_url}/pages/{page_id}",
                headers=self.headers,
                json={"properties": properties}
            )
            
            # Note: Updating block content requires fetching existing blocks,
            # deleting old ones, and creating new ones. This is simplified.
            print(f"✓ Updated Notion page for {doc_info['name']}")
        except Exception as e:
            print(f"⚠️  Error updating page for {doc_info['name']}: {e}")
    
    def find_existing_page(self, doc_path: str) -> Optional[str]:
        """Find existing page by path."""
        try:
            response = requests.post(
                f"{self.base_url}/databases/{self.database_id}/query",
                headers=self.headers,
                json={
                    "filter": {
                        "property": "Path",
                        "rich_text": {"equals": doc_path}
                    }
                }
            )
            response.raise_for_status()
            results = response.json().get("results", [])
            return results[0]["id"] if results else None
        except Exception:
            return None
    
    def sync_document(self, doc_info: Dict, root_path: Path) -> bool:
        """Sync a single document to Notion."""
        file_path = root_path / doc_info["path"]
        content = self.read_file_content(str(file_path))
        
        if not content:
            return False
        
        # Check if page exists
        existing_page_id = self.find_existing_page(doc_info["path"])
        
        if existing_page_id:
            self.update_page(existing_page_id, doc_info, content)
        else:
            page_id = self.create_page(doc_info, content)
            return page_id is not None
        
        return True
    
    def sync_all(self, inventory_path: str = "docs/document_inventory.json"):
        """Sync all documents from inventory."""
        inventory_file = Path(inventory_path)
        if not inventory_file.exists():
            print(f"❌ Inventory file not found: {inventory_path}")
            return
        
        with open(inventory_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        root_path = Path(data["metadata"]["root_path"])
        documents = data["documents"]
        
        print(f"📤 Syncing {len(documents)} documents to Notion...")
        
        synced = 0
        failed = 0
        
        for doc in documents:
            if self.sync_document(doc, root_path):
                synced += 1
            else:
                failed += 1
        
        print(f"\n✓ Synced: {synced}")
        if failed > 0:
            print(f"⚠️  Failed: {failed}")


def main():
    """Main entry point."""
    import sys
    
    notion_api_key = os.getenv("NOTION_API_KEY")
    database_id = os.getenv("NOTION_DATABASE_ID")
    
    if not notion_api_key:
        print("❌ NOTION_API_KEY environment variable not set")
        sys.exit(1)
    
    if not database_id:
        print("❌ NOTION_DATABASE_ID environment variable not set")
        sys.exit(1)
    
    sync = NotionSync(notion_api_key, database_id)
    sync.sync_all()


if __name__ == "__main__":
    main()

