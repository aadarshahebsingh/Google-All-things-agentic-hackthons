from google.adk.agents import Agent,SequentialAgent
from google.adk.models.lite_llm import LiteLlm
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from google.adk.tools import google_search


# AGENT_MODEL="ollama/qwen2.5:3b"
AGENT_MODEL="gemini-3.6-flash"

# destination research agent
destination_research_agent = Agent(
    name="destination_research_agent",

    model="AGENT_MODEL",

    description=(
        "A destination research specialist that gathers and summarizes "
        "information about travel destinations, including attractions, "
        "weather, best time to visit, local culture, and travel considerations."
    ),

    instruction="""
You are a Destination Research Agent specializing in travel research.

Your job is to research and provide useful, accurate, and structured
information about travel destinations.

When given a destination:

1. Identify the destination clearly.
2. Provide a brief overview of the destination.
3. List important attractions and activities.
4. Explain the best time of year to visit.
5. Describe the typical weather and climate.
6. Mention local culture, food, and experiences.
7. Mention important travel considerations.
8. Highlight anything that may be particularly useful for a traveler.
9. Do not invent information when reliable information is unavailable.
10. Keep your research organized and easy for another agent to consume.

If tools are available, use the appropriate tools to obtain information
instead of making assumptions.

Your output should be factual, concise, and structured so that a
Travel Planner Agent can use your research to create an itinerary.
""",

    tools=[
        [google_search],
    ],

    output_key="destination_research"
)


# itinerary_builder_agent
itinerary_builder_agent = Agent(
    name="itinerary_builder_agent",

    model="AGENT_MODEL",

    description=(
        "Creates detailed day-by-day travel itineraries using "
        "destination research and traveler preferences."
    ),

    instruction="""
Use the research stored in `destination_research` to create a
practical day-by-day travel itinerary.

- Organize the trip by day.
- Include morning, afternoon, and evening activities.
- Group nearby attractions together.
- Consider travel time, weather, budget, and traveler preferences.
- Include meal and rest breaks.
- Avoid overloading each day.
- Clearly mention optional activities.
- Do not invent information that is not available in the research.

Use the destination research as the primary source for selecting
destinations, attractions, and activities.
""",

    output_key="travel_itinerary"
)


# travel_optimizer: adds practical tips and optimizes 

travel_optimizer_agent = Agent(
    name="travel_optimizer_agent",

    model="AGENT_MODEL",

    description=(
        "Optimizes a travel itinerary to make it more efficient, "
        "balanced, practical, and enjoyable."
    ),

    instruction="""
Use the itinerary stored in `travel_itinerary` and optimize it.

- Reduce unnecessary travel and backtracking.
- Group nearby activities together.
- Balance the daily schedule.
- Avoid overcrowding the itinerary.
- Consider travel time, rest, meals, and practical sequencing.
- Preserve the important attractions from the original itinerary.
- Clearly identify any changes or optional activities.

Return the optimized itinerary in a clear day-by-day format.
""",

    output_key="optimized_itinerary"
)

def get_weather(city: str) -> dict:
    """
    Get the current weather for a city.

    Args:
        city: The name of the city.

    Returns:
        A dictionary containing weather information,
        or an error message if the city is not found.
    """

    print(f"[TOOL] get_weather called with city: {city}")

    # Normalize the city name
    city_normalized = city.strip().lower()

    print(f"[TOOL] Normalized city: {city_normalized}")

    # Mock weather database
    mock_weather_db = {
        "bangalore": {
            "temperature": 24,
            "condition": "Cloudy",
            "humidity": 78,
            "wind_speed": 9,
        },
        "mumbai": {
            "temperature": 29,
            "condition": "Sunny",
            "humidity": 72,
            "wind_speed": 14,
        },
        "delhi": {
            "temperature": 32,
            "condition": "Clear",
            "humidity": 45,
            "wind_speed": 11,
        },
        "goa": {
            "temperature": 28,
            "condition": "Partly Cloudy",
            "humidity": 70,
            "wind_speed": 15,
        },
    }

    print(f"[TOOL] Looking up weather for: {city_normalized}")

    # Check whether city exists
    if city_normalized not in mock_weather_db:
        print(f"[TOOL] City not found: {city_normalized}")

        return {
            "status": "error",
            "message": f"Weather data not available for {city}.",
        }

    # Get weather from mock database
    weather = mock_weather_db[city_normalized]

    print(f"[TOOL] Weather found: {weather}")

    return {
        "status": "success",
        "city": city,
        "temperature": weather["temperature"],
        "condition": weather["condition"],
        "humidity": weather["humidity"],
        "wind_speed": weather["wind_speed"],
    }




def get_current_time(timezone: str) -> dict:
    """
    Get the current date and time for a specified time zone.

    Args:
        timezone: IANA time-zone identifier, such as
                  'Asia/Kolkata', 'America/New_York',
                  'Europe/London', or 'Asia/Tokyo'.

    Returns:
        A dictionary containing the current date, time,
        time zone, and UTC offset.
    """

    print(f"[TOOL] get_current_time called with timezone: {timezone}")

    # Normalize input
    timezone_normalized = timezone.strip()

    print(f"[TOOL] Normalized timezone: {timezone_normalized}")

    # Validate timezone
    try:
        tz = ZoneInfo(timezone_normalized)
    except ZoneInfoNotFoundError:
        print(f"[TOOL] Invalid timezone: {timezone_normalized}")

        return {
            "status": "error",
            "message": f"Invalid IANA timezone: {timezone_normalized}",
            "example": "Use values such as 'Asia/Kolkata' or 'America/New_York'.",
        }

    # Get current time in requested timezone
    current_time = datetime.now(tz)

    # UTC offset
    utc_offset = current_time.strftime("%z")

    # Format UTC offset as +05:30 instead of +0530
    utc_offset_formatted = (
        f"{utc_offset[:3]}:{utc_offset[3:]}"
        if utc_offset
        else None
    )

    print(f"[TOOL] Current time: {current_time}")
    print(f"[TOOL] UTC offset: {utc_offset_formatted}")

    return {
        "status": "success",
        "timezone": timezone_normalized,
        "date": current_time.strftime("%Y-%m-%d"),
        "time": current_time.strftime("%H:%M:%S"),
        "datetime": current_time.isoformat(),
        "utc_offset": utc_offset_formatted,
    }



root_agent=Agent(
    name="travel_planner_agent",
    model=LiteLlm(AGENT_MODEL),
    # model=AGENT_MODEL,
    description="A comprehensive system planning agent that coordinates destination research, itinerary building, and optimization.",
    # tools=   Here tools are going to be there 
    tools=[get_weather, get_current_time]
)