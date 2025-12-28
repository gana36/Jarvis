"""Gmail Tool for fetching and summarizing Gmail messages using OAuth"""
import base64
import json
import logging
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any, Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import firebase_admin
from firebase_admin import firestore

logger = logging.getLogger(__name__)

# Default collection for credentials
CREDENTIALS_COLLECTION = "credentials"


class GmailTool:
    """Service for interacting with Gmail API using OAuth"""

    def __init__(self, user_id: str = "default"):
        """
        Initialize Gmail Tool with OAuth.
        
        Args:
            user_id: User identifier for data isolation
        """
        self.user_id = user_id
        self.service = None
        self._cache = {}  # Session-based cache
        self._cache_timestamp = None
        self._cache_ttl = 300  # Cache for 5 minutes
        
        # Initialize Firebase if needed
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
        
        self.db = firestore.client()
        
        # Load OAuth credentials
        self.credentials = self._load_credentials()
        
        if self.credentials and self.credentials.valid:
            self.service = build('gmail', 'v1', credentials=self.credentials)
            logger.info(f"✓ Gmail Tool initialized with OAuth for user: {user_id}")
        else:
            logger.warning("Gmail not authorized. User needs to connect Gmail via OAuth.")
            self.service = None

    def _load_credentials(self) -> Credentials | None:
        """
        Load OAuth credentials from Firestore.
        
        Returns:
            Credentials object or None if not authorized
        """
        try:
            # Load token data from Firestore
            doc_ref = self.db.collection('users').document(self.user_id).collection('credentials').document('gmail')
            doc = doc_ref.get()
            
            if not doc.exists:
                logger.info(f"No Gmail OAuth token found in Firestore for user {self.user_id}.")
                return None
            
            token_data = doc.to_dict()
            
            # Create credentials from token data
            creds = Credentials(
                token=token_data.get('token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri=token_data.get('token_uri'),
                client_id=token_data.get('client_id'),
                client_secret=token_data.get('client_secret'),
                scopes=token_data.get('scopes')
            )
            
            # Refresh if expired
            if creds.expired and creds.refresh_token:
                logger.info("Refreshing expired Gmail OAuth token...")
                creds.refresh(Request())
                
                # Save refreshed token
                self._save_credentials(creds)
                logger.info("✓ Gmail token refreshed successfully")
            
            return creds
            
        except Exception as e:
            logger.error(f"Failed to load Gmail credentials: {e}")
            return None
    
    def _save_credentials(self, creds: Credentials):
        """Save credentials to Firestore"""
        try:
            token_data = json.loads(creds.to_json())
            doc_ref = self.db.collection('users').document(self.user_id).collection('credentials').document('gmail')
            doc_ref.set(token_data)
            logger.info(f"✓ Saved Gmail credentials to Firestore for user {self.user_id}")
        except Exception as e:
            logger.error(f"Failed to save Gmail credentials: {e}")

    def get_recent_emails(self, max_results: int = 10, query: str = "") -> List[Dict[str, Any]]:
        """
        Fetch recent emails from Gmail.
        
        Args:
            max_results: Maximum number of emails to fetch (default 10)
            query: Gmail search query (e.g., "is:unread", "from:example@gmail.com")
            
        Returns:
            List of email dictionaries with id, subject, from, date, snippet
            Returns empty list if not authorized or API fails
        """
        cache_key = f"emails_{max_results}_{query}"
        
        # Check cache first
        if self._is_cache_valid() and cache_key in self._cache:
            logger.info("Returning cached emails")
            return self._cache.get(cache_key, [])
        
        if not self.service:
            logger.warning("Gmail service not available (not authorized)")
            return []
        
        try:
            # List messages
            results = self.service.users().messages().list(
                userId='me',
                maxResults=max_results,
                q=query
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                logger.info("No emails found")
                return []
            
            # Fetch full message details
            emails = []
            for msg in messages:
                try:
                    full_msg = self.service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='metadata',
                        metadataHeaders=['From', 'Subject', 'Date']
                    ).execute()
                    
                    # Extract headers
                    headers = {h['name']: h['value'] for h in full_msg.get('payload', {}).get('headers', [])}
                    
                    email_data = {
                        'id': msg['id'],
                        'threadId': full_msg.get('threadId'),
                        'subject': headers.get('Subject', '(No Subject)'),
                        'from': headers.get('From', 'Unknown'),
                        'date': headers.get('Date', ''),
                        'snippet': full_msg.get('snippet', ''),
                        'is_unread': 'UNREAD' in full_msg.get('labelIds', [])
                    }
                    emails.append(email_data)
                except Exception as e:
                    logger.warning(f"Failed to fetch email {msg['id']}: {e}")
                    continue
            
            # Cache the results
            self._cache[cache_key] = emails
            self._cache_timestamp = datetime.now()
            
            logger.info(f"✓ Fetched {len(emails)} emails")
            return emails
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to fetch emails: {e}")
            return []

    def get_unread_count(self) -> int:
        """
        Get count of unread emails in inbox.
        
        Returns:
            Number of unread emails
        """
        if not self.service:
            logger.warning("Gmail service not available (not authorized)")
            return 0
        
        try:
            # Use label info for fast unread count
            results = self.service.users().labels().get(
                userId='me',
                id='INBOX'
            ).execute()
            
            unread_count = results.get('messagesUnread', 0)
            logger.info(f"✓ Unread count: {unread_count}")
            return unread_count
            
        except Exception as e:
            logger.error(f"Failed to get unread count: {e}")
            return 0

    def get_today_emails(self) -> List[Dict[str, Any]]:
        """
        Fetch emails received today.
        
        Returns:
            List of today's emails
        """
        # Gmail query for emails from today
        today = datetime.now().strftime("%Y/%m/%d")
        query = f"after:{today}"
        return self.get_recent_emails(max_results=20, query=query)

    def get_email_details(self, message_id: str) -> Dict[str, Any]:
        """
        Get full details of a specific email.
        """
        if not self.service:
            return {}
        
        try:
            full_msg = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            headers = {h['name']: h['value'] for h in full_msg.get('payload', {}).get('headers', [])}
            body = self._extract_body(full_msg.get('payload', {}))
            
            return {
                'id': message_id,
                'threadId': full_msg.get('threadId'),
                'subject': headers.get('Subject', '(No Subject)'),
                'from': headers.get('From', 'Unknown'),
                'to': headers.get('To', ''),
                'date': headers.get('Date', ''),
                'body': body,
                'snippet': full_msg.get('snippet', ''),
                'labelIds': full_msg.get('labelIds', [])
            }
        except Exception as e:
            logger.error(f"Failed to get email details: {e}")
            return {}

    def get_thread_messages(self, thread_id: str) -> List[Dict[str, Any]]:
        """
        Fetch all messages in a thread.
        """
        if not self.service:
            return []
        
        try:
            thread = self.service.users().threads().get(
                userId='me',
                id=thread_id
            ).execute()
            
            messages = []
            for msg in thread.get('messages', []):
                headers = {h['name']: h['value'] for h in msg.get('payload', {}).get('headers', [])}
                body = self._extract_body(msg.get('payload', {}))
                
                messages.append({
                    'id': msg['id'],
                    'from': headers.get('From', 'Unknown'),
                    'date': headers.get('Date', ''),
                    'body': body,
                    'snippet': msg.get('snippet', '')
                })
            
            return messages
        except Exception as e:
            logger.error(f"Failed to fetch thread {thread_id}: {e}")
            return []

    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """
        Extract text body from email payload recursively.
        
        Args:
            payload: Email payload dict
            
        Returns:
            Extracted text body
        """
        body = ""
        
        if 'body' in payload and payload['body'].get('data'):
            # Decode base64url encoded body
            data = payload['body']['data']
            body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        
        # Check parts recursively
        if 'parts' in payload:
            for part in payload['parts']:
                mime_type = part.get('mimeType', '')
                if mime_type == 'text/plain':
                    if 'body' in part and part['body'].get('data'):
                        data = part['body']['data']
                        body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        break
                elif mime_type.startswith('multipart/'):
                    body = self._extract_body(part)
                    if body:
                        break
        
        return body

    def search_emails(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search emails using Gmail search syntax.
        
        Args:
            query: Gmail search query (e.g., "from:john subject:meeting")
            max_results: Maximum results to return
            
        Returns:
            List of matching emails
        """
        return self.get_recent_emails(max_results=max_results, query=query)

    def summarize_emails(self, emails: List[Dict[str, Any]]) -> str:
        """
        Create human-readable summary of emails.
        
        Args:
            emails: List of email dictionaries
            
        Returns:
            Human-readable summary string
        """
        if not emails:
            return "You have no new emails."
        
        email_count = len(emails)
        unread_count = sum(1 for e in emails if e.get('is_unread', False))
        
        # Build summary
        if email_count == 1:
            summary = "You have 1 recent email"
        else:
            summary = f"You have {email_count} recent emails"
        
        if unread_count > 0:
            summary += f" ({unread_count} unread)"
        
        summary += ": "
        
        # Add email snippets (top 3)
        email_descriptions = []
        for email in emails[:3]:
            sender = email.get('from', 'Unknown')
            # Extract just the name or email
            if '<' in sender:
                sender = sender.split('<')[0].strip()
            subject = email.get('subject', '(No Subject)')
            
            # Truncate subject if too long
            if len(subject) > 40:
                subject = subject[:37] + "..."
            
            email_descriptions.append(f"'{subject}' from {sender}")
        
        summary += ", ".join(email_descriptions)
        
        if email_count > 3:
            summary += f", and {email_count - 3} more"
        
        summary += "."
        
        return summary

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if not self._cache_timestamp:
            return False
        
        time_since_cache = (datetime.now() - self._cache_timestamp).total_seconds()
        return time_since_cache < self._cache_ttl


def get_gmail_tool(user_id: str = "default") -> GmailTool:
    """
    Get Gmail Tool instance.
    
    Args:
        user_id: User identifier for data isolation
        
    Returns:
        Configured GmailTool instance with OAuth
    """
    return GmailTool(user_id=user_id)
