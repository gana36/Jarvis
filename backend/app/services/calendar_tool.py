"""Calendar Tool for fetching and summarizing Google Calendar events using OAuth"""
import json
import logging
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import firebase_admin
from firebase_admin import credentials, firestore

logger = logging.getLogger(__name__)

# Default collection for credentials
CREDENTIALS_COLLECTION = "credentials"


class CalendarTool:
    """Service for interacting with Google Calendar API using OAuth"""

    def __init__(self, user_id: str = "default", calendar_id: str = "primary"):
        """
        Initialize Calendar Tool with OAuth.
        
        Args:
            user_id: User identifier for data isolation
            calendar_id: Calendar ID to use (default: "primary")
        """
        self.user_id = user_id
        self.calendar_id = calendar_id
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
            self.service = build('calendar', 'v3', credentials=self.credentials)
            logger.info(f"✓ Calendar Tool initialized with OAuth for calendar: {calendar_id}")
        else:
            logger.warning("Calendar not authorized. User needs to connect calendar via OAuth.")
            self.service = None

    def _load_credentials(self) -> Credentials | None:
        """
        Load OAuth credentials from Firestore.
        
        Returns:
            Credentials object or None if not authorized
        """
        try:
            # Load token data from Firestore
            doc_ref = self.db.collection('users').document(self.user_id).collection('credentials').document('google_calendar')
            doc = doc_ref.get()
            
            if not doc.exists:
                # Check for legacy token file just in case for "default" user
                if self.user_id == "default" and Path("calendar_token.json").exists():
                    logger.info("Migrating legacy calendar_token.json to Firestore...")
                    with open("calendar_token.json", 'r') as f:
                        token_data = json.load(f)
                    creds = Credentials(**token_data)
                    self._save_credentials(creds)
                    return creds
                
                logger.info(f"No OAuth token found in Firestore for user {self.user_id}.")
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
                logger.info("Refreshing expired OAuth token...")
                creds.refresh(Request())
                
                # Save refreshed token
                self._save_credentials(creds)
                logger.info("✓ Token refreshed successfully")
            
            return creds
            
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            return None
    
    def _save_credentials(self, creds: Credentials):
        """Save credentials to Firestore"""
        try:
            token_data = json.loads(creds.to_json())
            doc_ref = self.db.collection('users').document(self.user_id).collection('credentials').document('google_calendar')
            doc_ref.set(token_data)
            logger.info(f"✓ Saved credentials to Firestore for user {self.user_id}")
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")

    def get_today_events(self) -> List[Dict[str, Any]]:
        """
        Fetch events from Google Calendar for today.
        
        Returns:
            List of event dictionaries with id, summary, start, end, location
            Returns empty list if not authorized or API fails
        """
        # Check cache first
        if self._is_cache_valid():
            logger.info("Returning cached calendar events")
            return self._cache.get("events", [])
        
        if not self.service:
            logger.warning("Calendar service not available (not authorized)")
            return []
        
        try:
            # Get today's date range (start and end of day) with LOCAL timezone
            # Using timezone-aware datetime to avoid UTC conversion issues
            from datetime import timezone
            
            # Get current local time with timezone info
            now = datetime.now().astimezone()
            
            # Start of today (midnight local time)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            # End of today (11:59:59 PM local time)
            today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Convert to ISO format with timezone (Google Calendar API requires RFC3339)
            today_start_iso = today_start.isoformat()
            today_end_iso = today_end.isoformat()
            
            logger.info(f"Fetching events from {today_start_iso} to {today_end_iso}")
            
            # Call Calendar API
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=today_start_iso,
                timeMax=today_end_iso,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Transform to simplified structure
            simplified_events = []
            for event in events:
                simplified_event = {
                    'id': event.get('id', ''),
                    'summary': event.get('summary', 'Untitled Event'),
                    'start': event.get('start', {}).get('dateTime', event.get('start', {}).get('date', '')),
                    'end': event.get('end', {}).get('dateTime', event.get('end', {}).get('date', '')),
                    'location': event.get('location', ''),
                }
                simplified_events.append(simplified_event)
            
            # Cache the results
            self._cache['events'] = simplified_events
            self._cache_timestamp = datetime.now()
            
            logger.info(f"✓ Fetched {len(simplified_events)} events for today")
            return simplified_events
            
        except HttpError as e:
            logger.error(f"Calendar API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to fetch calendar events: {e}")
            return []

    def get_events_in_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Fetch events from Google Calendar for a specific date range.
        
        Args:
            start_date: Start datetime (timezone-aware)
            end_date: End datetime (timezone-aware)
            
        Returns:
            List of event dictionaries with id, summary, start, end, location
            Returns empty list if not authorized or API fails
        """
        if not self.service:
            logger.warning("Calendar service not available (not authorized)")
            return []
        
        try:
            # Convert to ISO format with timezone
            start_iso = start_date.isoformat()
            end_iso = end_date.isoformat()
            
            logger.info(f"Fetching events from {start_iso} to {end_iso}")
            
            # Call Calendar API
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=start_iso,
                timeMax=end_iso,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Transform to simplified structure
            simplified_events = []
            for event in events:
                simplified_event = {
                    'id': event.get('id', ''),
                    'summary': event.get('summary', 'Untitled Event'),
                    'start': event.get('start', {}).get('dateTime', event.get('start', {}).get('date', '')),
                    'end': event.get('end', {}).get('dateTime', event.get('end', {}).get('date', '')),
                    'location': event.get('location', ''),
                }
                simplified_events.append(simplified_event)
            
            logger.info(f"✓ Fetched {len(simplified_events)} events in range")
            return simplified_events
            
        except HttpError as e:
            logger.error(f"Calendar API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to fetch calendar events: {e}")
            return []

    def summarize_events(self, events: List[Dict[str, Any]]) -> str:
        """
        Create human-readable summary of events.
        
        Args:
            events: List of event dictionaries
            
        Returns:
            Human-readable summary string
        """
        if not events:
            return "You have no events scheduled for today."
        
        event_count = len(events)
        
        # Build summary
        if event_count == 1:
            summary = "You have 1 event today: "
        else:
            summary = f"You have {event_count} events today: "
        
        # Add event details
        event_descriptions = []
        for event in events:
            # Parse start time
            start_str = event.get('start', '')
            if start_str:
                try:
                    # Handle both datetime and date formats
                    if 'T' in start_str:
                        start_time = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                        time_str = start_time.strftime('%I:%M %p').lstrip('0')
                    else:
                        time_str = "all day"
                except Exception:
                    time_str = "unknown time"
            else:
                time_str = "unknown time"
            
            event_name = event.get('summary', 'Untitled')
            event_descriptions.append(f"{event_name} at {time_str}")
        
        summary += ", ".join(event_descriptions) + "."
        
        return summary

    # ========== Calendar Write Functions (for UI & Voice) ==========

    def create_event(
        self, 
        summary: str, 
        start_time: str, 
        end_time: str,
        description: str = "",
        location: str = ""
    ) -> Dict[str, Any]:
        """
        Create a new calendar event.
        
        Args:
            summary: Event title/summary
            start_time: Start time in ISO format (e.g., "2025-12-20T14:00:00-05:00")
            end_time: End time in ISO format
            description: Optional event description
            location: Optional event location
            
        Returns:
            Created event data or error dict
        """
        if not self.service:
            logger.error("Cannot create event: Calendar not authorized")
            return {"error": "Calendar not authorized"}
        
        try:
            event = {
                'summary': summary,
                'description': description,
                'location': location,
                'start': {'dateTime': start_time},
                'end': {'dateTime': end_time}
            }
            
            created_event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event
            ).execute()
            
            logger.info(f"✓ Created event: {summary}")
            
            # Invalidate cache
            self._cache_timestamp = None
            
            return {
                'id': created_event.get('id'),
                'summary': created_event.get('summary'),
                'start': created_event.get('start', {}).get('dateTime'),
                'htmlLink': created_event.get('htmlLink')
            }
            
        except Exception as e:
            logger.error(f"Failed to create event: {e}")
            return {"error": str(e)}

    def update_event(
        self,
        event_id: str,
        summary: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        description: str | None = None,
        location: str | None = None
    ) -> Dict[str, Any]:
        """
        Update an existing calendar event.
        
        Args:
            event_id: ID of event to update
            summary: New title (optional)
            start_time: New start time in ISO format (optional)
            end_time: New end time in ISO format (optional)
            description: New description (optional)
            location: New location (optional)
            
        Returns:
            Updated event data or error dict
        """
        if not self.service:
            logger.error("Cannot update event: Calendar not authorized")
            return {"error": "Calendar not authorized"}
        
        try:
            # Get existing event
            event = self.service.events().get(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            
            # Update fields if provided
            if summary is not None:
                event['summary'] = summary
            if description is not None:
                event['description'] = description
            if location is not None:
                event['location'] = location
            if start_time is not None:
                event['start'] = {'dateTime': start_time}
            if end_time is not None:
                event['end'] = {'dateTime': end_time}
            
            # Save updates
            updated_event = self.service.events().update(
                calendarId=self.calendar_id,
                eventId=event_id,
                body=event
            ).execute()
            
            logger.info(f"✓ Updated event: {event_id}")
            
            # Invalidate cache
            self._cache_timestamp = None
            
            return {
                'id': updated_event.get('id'),
                'summary': updated_event.get('summary'),
                'htmlLink': updated_event.get('htmlLink')
            }
            
        except Exception as e:
            logger.error(f"Failed to update event: {e}")
            return {"error": str(e)}

    def delete_event(self, event_id: str) -> Dict[str, Any]:
        """
        Delete a calendar event.
        
        Args:
            event_id: ID of event to delete
            
        Returns:
            Success status or error dict
        """
        if not self.service:
            logger.error("Cannot delete event: Calendar not authorized")
            return {"error": "Calendar not authorized"}
        
        try:
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            
            logger.info(f"✓ Deleted event: {event_id}")
            
            # Invalidate cache
            self._cache_timestamp = None
            
            return {"success": True, "message": f"Event {event_id} deleted"}
            
        except Exception as e:
            logger.error(f"Failed to delete event: {e}")
            return {"error": str(e)}

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if not self._cache_timestamp:
            return False
        
        time_since_cache = (datetime.now() - self._cache_timestamp).total_seconds()
        return time_since_cache < self._cache_ttl


def get_calendar_tool(user_id: str = "default") -> CalendarTool:
    """
    Get Calendar Tool instance.
    
    Args:
        user_id: User identifier for data isolation
        
    Returns:
        Configured CalendarTool instance with OAuth
    """
    return CalendarTool(user_id=user_id, calendar_id="primary")
