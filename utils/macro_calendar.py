from datetime import datetime, timedelta
import requests

def get_upcoming_economic_events(days=30):
    """
    Simulates fetching upcoming major economic events.
    In a real production environment, this would call an API like Alpha Vantage, Fred, or Investing.com.
    
    For now, we return a standard schedule logic and some critical fixed events relative to current date.
    Current Date: {datetime.now().strftime('%Y-%m-%d')}
    """
    today = datetime.now()
    events = []
    
    # 1. Define Standard Monthly Patterns (Simulated)
    # CPI: Usually around 12th-15th
    # FOMC: Roughly every 6 weeks. Let's add simulated dates.
    # Jobs Report (NFP): 1st Friday of the month
    
    target_end_date = today + timedelta(days=days)
    
    # Generate potential events for the next month
    candidates = [
        {"name": "FOMC Meeting Decision", "day": 20, "impact": "HIGH"}, # Simulated: 20th
        {"name": "US CPI (Inflation Data)", "day": 13, "impact": "HIGH"},    # Simulated: 13th
        {"name": "Non-Farm Payrolls (Jobs)", "day": 5, "impact": "HIGH"},     # Simulated: 5th
        {"name": "GDP Growth Rate", "day": 28, "impact": "MEDIUM"},          # Simulated: 28th
        {"name": "Retail Sales", "day": 15, "impact": "MEDIUM"},             # Simulated: 15th
    ]
    
    # Check if these dates fall within our range (today ~ today+days)
    # We check for the current month and next month
    months_to_check = [today, today + timedelta(days=32)]
    
    for m in months_to_check:
        for ev in candidates:
            try:
                # Create specific date object for the event in this month
                # Handle cases where day might not exist (e.g. Feb 30)
                event_date = datetime(m.year, m.month, ev["day"])
                
                if today <= event_date <= target_end_date:
                    days_left = (event_date - today).days
                    events.append({
                        "date": event_date.strftime("%Y-%m-%d"),
                        "event": ev["name"],
                        "impact": ev["impact"],
                        "days_left": days_left
                    })
            except ValueError:
                continue # Skip invalid dates
                
    # Sort by date
    events.sort(key=lambda x: x['date'])
    
    return events

def get_macro_context() -> str:
    """
    Returns a summarized string of upcoming macro events for AI context.
    """
    events = get_upcoming_economic_events()
    if not events:
        return "No major economic events scheduled for the next 30 days."
    
    summary = "📅 Upcoming Economic Events (Next 30 Days):\n"
    for ev in events:
        icon = "🔥" if ev['impact'] == "HIGH" else "▪️"
        summary += f"- {ev['date']} (D-{ev['days_left']}): {icon} {ev['event']} [{ev['impact']}]\n"
        
    return summary.strip()
