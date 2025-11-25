"""Timezone utility functions for CET/CEST conversion."""
import pytz
import logging
from datetime import datetime
from typing import Union, Optional

logger = logging.getLogger(__name__)

# Define the timezone for Netherlands/Belgium (handles CET/CEST automatically)
# CET = Central European Time (UTC+1) - Winter
# CEST = Central European Summer Time (UTC+2) - Summer
LOCAL_TIMEZONE = pytz.timezone('Europe/Amsterdam')

def utc_to_local(utc_time: Union[datetime, str, None]) -> Optional[datetime]:
    """
    Convert UTC time to local time (CET/CEST).
    Automatically handles daylight saving time transitions.
    
    Args:
        utc_time: UTC datetime object or ISO format string
        
    Returns:
        Datetime object in local timezone (CET/CEST) or None
    """
    if utc_time is None:
        return None
    
    try:
        # If string, parse it
        if isinstance(utc_time, str):
            # Handle various ISO formats
            utc_time = utc_time.replace('Z', '+00:00')
            utc_dt = datetime.fromisoformat(utc_time)
        else:
            utc_dt = utc_time
        
        # Ensure it's timezone-aware (UTC)
        if utc_dt.tzinfo is None:
            utc_dt = pytz.utc.localize(utc_dt)
        
        # Convert to local timezone
        local_dt = utc_dt.astimezone(LOCAL_TIMEZONE)
        
        return local_dt

    except Exception as e:
        logger.error(f"Error converting UTC to local time: {e}")
        return None

def local_to_utc(local_time: Union[datetime, str, None]) -> Optional[datetime]:
    """
    Convert local time (CET/CEST) to UTC.
    Automatically handles daylight saving time transitions.
    
    Args:
        local_time: Local datetime object or ISO format string
        
    Returns:
        Datetime object in UTC or None
    """
    if local_time is None:
        return None
    
    try:
        # If string, parse it
        if isinstance(local_time, str):
            local_dt = datetime.fromisoformat(local_time)
        else:
            local_dt = local_time
        
        # Localize to local timezone if naive
        if local_dt.tzinfo is None:
            local_dt = LOCAL_TIMEZONE.localize(local_dt)
        
        # Convert to UTC
        utc_dt = local_dt.astimezone(pytz.utc)
        
        return utc_dt
        
    except Exception as e:
        print(f"Error converting local to UTC time: {e}")
        return None

def format_datetime(dt: Union[datetime, str, None], 
                   include_timezone: bool = True,
                   date_format: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    Format datetime for display in local timezone.
    
    Args:
        dt: Datetime object or ISO string (assumed UTC)
        include_timezone: Whether to include timezone abbreviation (CET/CEST)
        date_format: strftime format string
        
    Returns:
        Formatted datetime string in local timezone
    """
    if dt is None:
        return 'N/A'
    
    try:
        # Convert to local timezone
        local_dt = utc_to_local(dt)
        
        if local_dt is None:
            return 'N/A'
        
        # Format the datetime
        formatted = local_dt.strftime(date_format)
        
        # Add timezone abbreviation if requested
        if include_timezone:
            # Get the timezone name (CET or CEST)
            tz_name = local_dt.strftime('%Z')
            formatted = f"{formatted} {tz_name}"
        
        return formatted
        
    except Exception as e:
        print(f"Error formatting datetime: {e}")
        return str(dt) if dt else 'N/A'

def get_current_local_time() -> datetime:
    """
    Get current time in local timezone (CET/CEST).
    
    Returns:
        Current datetime in local timezone
    """
    return datetime.now(LOCAL_TIMEZONE)

def get_current_utc_time() -> datetime:
    """
    Get current time in UTC.
    
    Returns:
        Current datetime in UTC
    """
    return datetime.now(pytz.utc)

def get_timezone_info() -> dict:
    """
    Get information about current timezone.
    
    Returns:
        Dictionary with timezone information
    """
    now = datetime.now(LOCAL_TIMEZONE)
    
    return {
        'timezone': 'Europe/Amsterdam',
        'current_abbreviation': now.strftime('%Z'),  # CET or CEST
        'utc_offset': now.strftime('%z'),  # +0100 or +0200
        'is_dst': bool(now.dst()),  # True if CEST (summer), False if CET (winter)
    }

# Convenience function for common use case
def format_timestamp(iso_string: str) -> str:
    """
    Quick format for ISO timestamp strings from database.
    
    Args:
        iso_string: ISO format timestamp string (UTC)
        
    Returns:
        Formatted string in local timezone
    """
    return format_datetime(iso_string, include_timezone=True)