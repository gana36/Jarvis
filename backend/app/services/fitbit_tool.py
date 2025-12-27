"""Fitbit Tool for fetching health data using OAuth"""
import base64
import json
import logging
import time
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import requests

from app.config import get_settings

logger = logging.getLogger(__name__)

# Token storage path
TOKEN_FILE = Path("fitbit_token.json")


class FitbitTool:
    """Service for interacting with Fitbit API using OAuth"""

    def __init__(self):
        """Initialize Fitbit Tool with OAuth credentials"""
        self.api_base = "https://api.fitbit.com"
        self.credentials = self._load_credentials()

        if self.credentials:
            logger.info("✓ Fitbit Tool initialized with OAuth")
        else:
            logger.warning("Fitbit not authorized. User needs to connect via OAuth.")

    def _load_credentials(self) -> Dict[str, Any] | None:
        """
        Load OAuth credentials from token file.

        Returns:
            Credentials dict or None if not authorized
        """
        if not TOKEN_FILE.exists():
            logger.info("No Fitbit OAuth token found. User needs to authorize.")
            return None

        try:
            with open(TOKEN_FILE, 'r') as f:
                token_data = json.load(f)

            # Validate required fields
            required_fields = ['access_token', 'refresh_token', 'expires_at']
            if not all(field in token_data for field in required_fields):
                logger.error("Invalid token file: missing required fields")
                return None

            return token_data

        except Exception as e:
            logger.error(f"Failed to load Fitbit credentials: {e}")
            return None

    def _refresh_token_if_expired(self) -> bool:
        """
        Check if token is expired and refresh if needed.

        Returns:
            True if token is valid (or was refreshed), False otherwise
        """
        if not self.credentials:
            return False

        # Check if token is expired
        current_time = int(time.time())
        expires_at = self.credentials.get('expires_at', 0)

        if current_time < expires_at:
            # Token is still valid
            return True

        # Token expired, refresh it
        logger.info("Fitbit access token expired, refreshing...")

        try:
            settings = get_settings()

            # Prepare Basic Auth header
            credentials_str = f"{settings.fitbit_client_id}:{settings.fitbit_client_secret}"
            encoded_credentials = base64.b64encode(credentials_str.encode()).decode()

            # Request new access token
            token_url = f"{self.api_base}/oauth2/token"
            headers = {
                "Authorization": f"Basic {encoded_credentials}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.credentials.get('refresh_token')
            }

            response = requests.post(token_url, headers=headers, data=data)
            response.raise_for_status()

            token_response = response.json()

            # Update credentials
            new_expires_at = int(time.time()) + token_response.get('expires_in', 28800)
            self.credentials['access_token'] = token_response.get('access_token')
            self.credentials['refresh_token'] = token_response.get('refresh_token')
            self.credentials['expires_at'] = new_expires_at

            # Save updated credentials
            with open(TOKEN_FILE, 'w') as f:
                json.dump(self.credentials, f, indent=2)

            logger.info("✓ Fitbit token refreshed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to refresh Fitbit token: {e}")
            return False

    def _make_request(self, endpoint: str) -> Dict[str, Any] | None:
        """
        Make authenticated request to Fitbit API.

        Args:
            endpoint: API endpoint path (e.g., "/1/user/-/activities/date/2024-01-15.json")

        Returns:
            JSON response dict or None on failure
        """
        if not self._refresh_token_if_expired():
            logger.warning("Cannot make Fitbit API request: not authorized or token refresh failed")
            return None

        # MOCK DATA: Return mock responses for testing (no real Fitbit device required)
        if self.credentials.get('user_id') == 'MOCK_USER':
            logger.info(f"Returning mock data for endpoint: {endpoint}")

            # Extract date from endpoint for date-varying mock data
            import re
            date_match = re.search(r'/(\d{4}-\d{2}-\d{2})', endpoint)
            day_offset = 0
            if date_match:
                # Calculate day offset from today for variation
                from datetime import datetime
                endpoint_date = datetime.strptime(date_match.group(1), '%Y-%m-%d')
                today = datetime.now()
                day_offset = (today - endpoint_date).days

            # Generate pseudo-random but consistent values based on day offset
            # Using simple math to create variation (not truly random, but deterministic)
            sleep_variation = (day_offset * 17) % 120  # 0-120 minute variation
            step_variation = (day_offset * 311) % 4000  # 0-4000 step variation
            hr_variation = (day_offset * 7) % 12  # 0-12 bpm variation

            # Mock sleep data
            if '/sleep/date/' in endpoint:
                base_sleep = 420  # 7 hours base
                total_sleep = base_sleep + sleep_variation
                efficiency = 75 + (day_offset * 3) % 20  # 75-95%

                return {
                    "summary": {
                        "totalMinutesAsleep": total_sleep,
                        "totalTimeInBed": total_sleep + 20 + (day_offset % 30)
                    },
                    "sleep": [{
                        "isMainSleep": True,
                        "efficiency": efficiency,
                        "levels": {
                            "summary": {
                                "deep": {"minutes": int(total_sleep * 0.20)},
                                "light": {"minutes": int(total_sleep * 0.50)},
                                "rem": {"minutes": int(total_sleep * 0.25)},
                                "wake": {"minutes": int(total_sleep * 0.05)}
                            }
                        }
                    }]
                }

            # Mock activity data
            elif '/activities/date/' in endpoint and '/heart/' not in endpoint:
                base_steps = 6000
                steps = base_steps + step_variation
                distance = round(steps * 0.0005, 2)  # ~0.5 miles per 1000 steps
                calories = 1800 + int(steps * 0.04)  # Base + activity calories

                return {
                    "summary": {
                        "steps": steps,
                        "distances": [{"distance": distance}],
                        "caloriesOut": calories,
                        "fairlyActiveMinutes": 15 + (day_offset * 5) % 40,
                        "veryActiveMinutes": 10 + (day_offset * 3) % 30,
                        "floors": 8 + (day_offset * 2) % 15
                    }
                }

            # Mock heart rate data
            elif '/activities/heart/' in endpoint:
                resting_hr = 60 + hr_variation

                return {
                    "activities-heart": [{
                        "value": {
                            "restingHeartRate": resting_hr,
                            "heartRateZones": [
                                {"name": "Out of Range", "minutes": 1200, "caloriesOut": 1500},
                                {"name": "Fat Burn", "minutes": 100 + (day_offset * 5) % 50, "caloriesOut": 350},
                                {"name": "Cardio", "minutes": 20 + (day_offset * 3) % 40, "caloriesOut": 200},
                                {"name": "Peak", "minutes": 5 + (day_offset * 2) % 20, "caloriesOut": 106}
                            ]
                        }
                    }]
                }

            return None

        try:
            url = f"{self.api_base}{endpoint}"
            headers = {
                "Authorization": f"Bearer {self.credentials.get('access_token')}"
            }

            response = requests.get(url, headers=headers)
            response.raise_for_status()

            return response.json()

        except requests.exceptions.HTTPError as e:
            logger.error(f"Fitbit API HTTP error for {endpoint}: {e}")
            return None
        except Exception as e:
            logger.error(f"Fitbit API request failed for {endpoint}: {e}")
            return None

    def get_sleep_data(self, date: datetime | None = None) -> Dict[str, Any]:
        """
        Fetch sleep data for a specific date.

        Args:
            date: Date to fetch sleep data for (default: yesterday, since sleep data is for previous night)

        Returns:
            Dict with sleep data or empty dict if not available
        """
        if date is None:
            # Default to yesterday (sleep is for the previous night)
            date = datetime.now() - timedelta(days=1)

        date_str = date.strftime("%Y-%m-%d")
        endpoint = f"/1.2/user/-/sleep/date/{date_str}.json"

        response = self._make_request(endpoint)
        if not response:
            return {}

        # Extract sleep summary
        sleep_summary = response.get('summary', {})

        # Get main sleep entry (longest sleep)
        sleep_entries = response.get('sleep', [])
        main_sleep = None
        if sleep_entries:
            # Find the main sleep (isMainSleep=True or longest duration)
            main_sleep = next((s for s in sleep_entries if s.get('isMainSleep')), sleep_entries[0])

        result = {
            'totalMinutesAsleep': sleep_summary.get('totalMinutesAsleep', 0),
            'totalTimeInBed': sleep_summary.get('totalTimeInBed', 0),
            'efficiency': main_sleep.get('efficiency', 0) if main_sleep else 0,
        }

        # Extract sleep stages if available
        if main_sleep and 'levels' in main_sleep:
            stages = main_sleep['levels'].get('summary', {})
            result['stages'] = {
                'deep': stages.get('deep', {}).get('minutes', 0),
                'light': stages.get('light', {}).get('minutes', 0),
                'rem': stages.get('rem', {}).get('minutes', 0),
                'wake': stages.get('wake', {}).get('minutes', 0)
            }

        return result

    def get_activity_data(self, date: datetime | None = None) -> Dict[str, Any]:
        """
        Fetch activity data (steps, distance, calories) for a specific date.

        Args:
            date: Date to fetch activity data for (default: today)

        Returns:
            Dict with activity data or empty dict if not available
        """
        if date is None:
            date = datetime.now()

        date_str = date.strftime("%Y-%m-%d")
        endpoint = f"/1/user/-/activities/date/{date_str}.json"

        response = self._make_request(endpoint)
        if not response:
            return {}

        summary = response.get('summary', {})

        result = {
            'steps': summary.get('steps', 0),
            'distance': round(summary.get('distances', [{}])[0].get('distance', 0), 2) if summary.get('distances') else 0,
            'caloriesOut': summary.get('caloriesOut', 0),
            'activeMinutes': summary.get('fairlyActiveMinutes', 0) + summary.get('veryActiveMinutes', 0),
            'floors': summary.get('floors', 0)
        }

        return result

    def get_heart_rate_data(self, date: datetime | None = None) -> Dict[str, Any]:
        """
        Fetch heart rate data for a specific date.

        Args:
            date: Date to fetch heart rate data for (default: today)

        Returns:
            Dict with heart rate data or empty dict if not available
        """
        if date is None:
            date = datetime.now()

        date_str = date.strftime("%Y-%m-%d")
        endpoint = f"/1/user/-/activities/heart/date/{date_str}/1d.json"

        response = self._make_request(endpoint)
        if not response:
            return {}

        # Extract resting heart rate
        activities_heart = response.get('activities-heart', [])
        if not activities_heart:
            return {}

        heart_data = activities_heart[0].get('value', {})

        result = {
            'restingHeartRate': heart_data.get('restingHeartRate', 0)
        }

        # Extract heart rate zones if available
        heart_rate_zones = heart_data.get('heartRateZones', [])
        if heart_rate_zones:
            result['zones'] = {}
            for zone in heart_rate_zones:
                zone_name = zone.get('name', '').lower().replace(' ', '_')
                result['zones'][zone_name] = {
                    'minutes': zone.get('minutes', 0),
                    'caloriesOut': zone.get('caloriesOut', 0)
                }

        return result

    def get_daily_summary(self, date: datetime | None = None) -> str:
        """
        Get human-readable summary of health data for a date.

        Args:
            date: Date to get summary for (default: today for activity/heart, yesterday for sleep)

        Returns:
            Formatted health summary string or empty string if no data available
        """
        if not self.credentials:
            return ""

        summary_parts = []

        # Get sleep data (for previous night)
        sleep = self.get_sleep_data(date)
        if sleep and sleep.get('totalMinutesAsleep', 0) > 0:
            hours = sleep['totalMinutesAsleep'] // 60
            minutes = sleep['totalMinutesAsleep'] % 60
            efficiency = sleep.get('efficiency', 0)
            summary_parts.append(f"You slept {hours}h {minutes}m last night with a sleep efficiency of {efficiency}%")

        # Get activity data
        activity = self.get_activity_data(date)
        if activity and activity.get('steps', 0) > 0:
            steps = activity['steps']
            distance = activity['distance']
            calories = activity['caloriesOut']
            summary_parts.append(f"You've walked {steps:,} steps covering {distance} miles and burned {calories:,} calories today")

        # Get heart rate data
        heart = self.get_heart_rate_data(date)
        if heart and heart.get('restingHeartRate', 0) > 0:
            rhr = heart['restingHeartRate']
            summary_parts.append(f"Your resting heart rate is {rhr} bpm")

        return "\n".join(summary_parts)


@lru_cache
def get_fitbit_tool() -> FitbitTool:
    """
    Get cached Fitbit Tool instance (singleton pattern).

    Returns:
        Configured FitbitTool instance
    """
    return FitbitTool()
