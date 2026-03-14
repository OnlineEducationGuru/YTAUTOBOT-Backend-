"""
Scheduler Service - Peak time management
"""

from datetime import datetime, timedelta


# Peak times in IST (Indian Standard Time)
YOUTUBE_PEAK = {
    0: ["11:00", "17:00", "20:00"],  # Monday
    1: ["11:00", "17:00", "20:00"],  # Tuesday
    2: ["11:00", "17:00", "20:00"],  # Wednesday
    3: ["11:00", "17:00", "20:00"],  # Thursday
    4: ["11:00", "17:00", "21:00"],  # Friday
    5: ["10:00", "16:00", "21:00"],  # Saturday
    6: ["10:00", "16:00", "20:00"],  # Sunday
}

FACEBOOK_PEAK = {
    0: ["13:00", "19:00"],
    1: ["13:00", "19:00"],
    2: ["13:00", "19:00"],
    3: ["13:00", "19:00"],
    4: ["13:00", "20:00"],
    5: ["12:00", "20:00"],
    6: ["12:00", "19:00"],
}


def get_next_peak_time(platform="youtube"):
    """Get next peak posting time"""
    peak_times = YOUTUBE_PEAK if platform == "youtube" else FACEBOOK_PEAK
    
    now = datetime.now()
    current_day = now.weekday()
    current_time = now.strftime("%H:%M")
    
    # Check today's remaining times
    for time_str in peak_times.get(current_day, []):
        if time_str > current_time:
            hour, minute = map(int, time_str.split(":"))
            return now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # Tomorrow's first time
    tomorrow = (now + timedelta(days=1))
    tomorrow_day = tomorrow.weekday()
    times = peak_times.get(tomorrow_day, ["12:00"])
    hour, minute = map(int, times[0].split(":"))
    return tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)