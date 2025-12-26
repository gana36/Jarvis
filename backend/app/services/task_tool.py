"""Task Tool for managing tasks in Firestore"""
import logging
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, List

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import FieldFilter

logger = logging.getLogger(__name__)


class TaskTool:
    """Service for managing tasks in Google Firestore"""

    def __init__(self, user_id: str = "default"):
        """
        Initialize Task Tool with Firestore.
        
        Args:
            user_id: User identifier for data isolation. 
                    - "default": Uses global /tasks collection (backward compatible)
                    - Any other value: Uses /users/{user_id}/tasks collection
        """
        # Initialize Firebase Admin if not already done
        if not firebase_admin._apps:
            try:
                # Use default credentials (same as Calendar/Speech-to-Text)
                # This reads from GOOGLE_APPLICATION_CREDENTIALS environment variable
                import os
                cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
                
                if cred_path:
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred)
                    logger.info(f"✓ Firebase Admin initialized with credentials from {cred_path}")
                else:
                    # Try default credentials
                    firebase_admin.initialize_app()
                    logger.info("✓ Firebase Admin initialized with default credentials")
                    
            except Exception as e:
                logger.error(f"Failed to initialize Firebase Admin: {e}")
                raise
        
        # Get Firestore client
        self.db = firestore.client()
        self.user_id = user_id
        
        # Use user-scoped collection for authenticated users, global collection for default
        if user_id == "default":
            self.collection = self.db.collection('tasks')
            logger.info("✓ Task Tool initialized with global tasks collection")
        else:
            self.collection = self.db.collection('users').document(user_id).collection('tasks')
            logger.info(f"✓ Task Tool initialized for user: {user_id}")

    def add_task(
        self,
        title: str,
        status: str = "pending",
        priority: str | None = None,
        due_date: datetime | None = None
    ) -> Dict[str, Any]:
        """
        Create a new task in Firestore.
        
        Args:
            title: Task title/description
            status: Task status (default: "pending")
            priority: Task priority ("high", "medium", "low", or None)
            due_date: Optional due date
            
        Returns:
            Created task data with auto-generated ID
        """
        try:
            now = datetime.now()
            
            # Prepare task data
            task_data = {
                'title': title,
                'status': status,
                'priority': priority,
                'due_date': due_date,
                'created_at': now,
                'updated_at': now,
            }
            
            # Add to Firestore
            doc_ref = self.collection.add(task_data)
            task_id = doc_ref[1].id
            
            logger.info(f"✓ Created task: {task_id} - {title}")
            
            # Return task with ID
            return {
                'id': task_id,
                'title': title,
                'status': status,
                'priority': priority,
                'due_date': due_date.isoformat() if due_date else None,
                'created_at': now.isoformat(),
                'updated_at': now.isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            raise

    def list_tasks(self, status_filter: str | None = None) -> List[Dict[str, Any]]:
        """
        List all tasks from Firestore.
        
        Args:
            status_filter: Optional status to filter by (e.g., "pending", "completed")
            
        Returns:
            List of task dictionaries
        """
        try:
            # Build query
            query = self.collection
            
            if status_filter:
                query = query.where(filter=FieldFilter('status', '==', status_filter))
            
            # Only order by created_at if NOT filtering by status (avoids composite index requirement)
            if not status_filter:
                query = query.order_by('created_at', direction=firestore.Query.DESCENDING)
            
            # Execute query
            docs = query.stream()
            
            # Convert to list of dicts
            tasks = []
            for doc in docs:
                task_data = doc.to_dict()
                task_data['id'] = doc.id
                
                # Convert timestamps to ISO strings
                if task_data.get('created_at'):
                    task_data['created_at'] = task_data['created_at'].isoformat()
                if task_data.get('updated_at'):
                    task_data['updated_at'] = task_data['updated_at'].isoformat()
                if task_data.get('due_date'):
                    task_data['due_date'] = task_data['due_date'].isoformat()
                
                tasks.append(task_data)
            
            # Sort in Python if we filtered (since we couldn't order in query)
            if status_filter and tasks:
                tasks.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            logger.info(f"✓ Listed {len(tasks)} tasks (filter: {status_filter or 'none'})")
            return tasks
            
        except Exception as e:
            logger.error(f"Failed to list tasks: {e}")
            return []

    def get_task(self, task_id: str) -> Dict[str, Any] | None:
        """
        Get a single task by ID.
        
        Args:
            task_id: Firestore document ID
            
        Returns:
            Task data or None if not found
        """
        try:
            doc = self.collection.document(task_id).get()
            
            if not doc.exists:
                logger.warning(f"Task not found: {task_id}")
                return None
            
            task_data = doc.to_dict()
            task_data['id'] = doc.id
            
            # Convert timestamps to ISO strings
            if task_data.get('created_at'):
                task_data['created_at'] = task_data['created_at'].isoformat()
            if task_data.get('updated_at'):
                task_data['updated_at'] = task_data['updated_at'].isoformat()
            if task_data.get('due_date'):
                task_data['due_date'] = task_data['due_date'].isoformat()
            
            logger.info(f"✓ Retrieved task: {task_id}")
            return task_data
            
        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {e}")
            return None

    def update_task(
        self,
        task_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        """
        Update task fields in Firestore.
        
        Args:
            task_id: Firestore document ID
            updates: Dictionary of fields to update (title, status, priority, due_date)
            
        Returns:
            Updated task data or None if not found
        """
        try:
            doc_ref = self.collection.document(task_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                logger.warning(f"Task not found for update: {task_id}")
                return None
            
            # Add updated_at timestamp
            updates['updated_at'] = datetime.now()
            
            # Update in Firestore
            doc_ref.update(updates)
            
            # Get updated document
            updated_doc = doc_ref.get()
            task_data = updated_doc.to_dict()
            task_data['id'] = task_id
            
            # Convert timestamps to ISO strings
            if task_data.get('created_at'):
                task_data['created_at'] = task_data['created_at'].isoformat()
            if task_data.get('updated_at'):
                task_data['updated_at'] = task_data['updated_at'].isoformat()
            if task_data.get('due_date'):
                task_data['due_date'] = task_data['due_date'].isoformat()
            
            logger.info(f"✓ Updated task: {task_id}")
            return task_data
            
        except Exception as e:
            logger.error(f"Failed to update task {task_id}: {e}")
            return None

    def delete_task(self, task_id: str) -> bool:
        """
        Delete task from Firestore.
        
        Args:
            task_id: Firestore document ID
            
        Returns:
            True if deleted, False if not found
        """
        try:
            doc_ref = self.collection.document(task_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                logger.warning(f"Task not found for deletion: {task_id}")
                return False
            
            # Delete from Firestore
            doc_ref.delete()
            
            logger.info(f"✓ Deleted task: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete task {task_id}: {e}")
            return False

    def mark_complete(self, task_id: str) -> Dict[str, Any] | None:
        """
        Mark task as completed.
        
        Args:
            task_id: Firestore document ID
            
        Returns:
           Updated task data or None if not found
        """
        return self.update_task(task_id, {"status": "completed"})

    def mark_incomplete(self, task_id: str) -> Dict[str, Any] | None:
        """
        Mark task as pending (undo completion).
        
        Args:
            task_id: Firestore document ID
            
        Returns:
            Updated task data or None if not found
        """
        return self.update_task(task_id, {"status": "pending"})



@lru_cache
def get_task_tool(user_id: str = "default") -> TaskTool:
    """
    Get cached Task Tool instance.
    
    Args:
        user_id: User identifier for data isolation (default: "default" for global collection)
    
    Returns:
        Configured TaskTool instance with Firestore
    """
    return TaskTool(user_id)
