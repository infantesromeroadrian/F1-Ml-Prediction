"""Interactive session selector for F1 Race Replay."""

import logging
from typing import Literal

import fastf1

logger = logging.getLogger(__name__)

SessionType = Literal["R", "S", "Q", "SQ"]


def interactive_session_selector() -> tuple[int, int, SessionType]:
    """
    Interactive CLI to select F1 session.

    Returns:
        Tuple of (year, round_number, session_type)
    """
    print("\n" + "=" * 80)
    print(" " * 20 + "🏎️  F1 RACE REPLAY - SESSION SELECTOR 🏎️")
    print("=" * 80 + "\n")

    # Step 1: Select Year
    print("📅 Available Years: 2018-2025")
    while True:
        try:
            year_input = input("Enter year (default: 2024): ").strip()
            year = int(year_input) if year_input else 2024

            if 2018 <= year <= 2025:
                break
            else:
                print("❌ Year must be between 2018 and 2025. Try again.")
        except ValueError:
            print("❌ Invalid input. Please enter a number.")

    print(f"\n✅ Selected year: {year}\n")

    # Step 2: Fetch and display available rounds
    print("🔍 Fetching race calendar...")
    try:
        schedule = fastf1.get_event_schedule(year, include_testing=False)
        print(f"\n🏁 {year} F1 Season - {len(schedule)} Rounds\n")
        print("-" * 80)
        print(f"{'Round':<8} {'Date':<15} {'Location':<30} {'Event Name':<30}")
        print("-" * 80)

        for idx, event in schedule.iterrows():
            round_num = event["RoundNumber"]
            date = event["EventDate"].strftime("%Y-%m-%d")
            location = event["Location"]
            event_name = event["EventName"]
            print(f"{round_num:<8} {date:<15} {location:<30} {event_name:<30}")

        print("-" * 80)

    except Exception as e:
        logger.error(f"Failed to fetch schedule: {e}")
        print(f"❌ Could not fetch calendar for {year}. Using default round.")
        return year, 1, "R"

    # Step 3: Select Round
    max_round = int(schedule["RoundNumber"].max())
    while True:
        try:
            round_input = input(f"\nEnter round number (1-{max_round}, default: 1): ").strip()
            round_number = int(round_input) if round_input else 1

            if 1 <= round_number <= max_round:
                break
            else:
                print(f"❌ Round must be between 1 and {max_round}. Try again.")
        except ValueError:
            print("❌ Invalid input. Please enter a number.")

    # Get event name for selected round
    selected_event = schedule[schedule["RoundNumber"] == round_number].iloc[0]
    event_name = selected_event["EventName"]
    event_date = selected_event["EventDate"].strftime("%Y-%m-%d")

    print(f"\n✅ Selected round: {round_number} - {event_name} ({event_date})\n")

    # Step 4: Select Session Type
    print("📺 Available Sessions:")
    print("  [R]  Race (default)")
    print("  [Q]  Qualifying")
    print("  [S]  Sprint")
    print("  [SQ] Sprint Qualifying")

    session_map = {
        "r": "R",
        "q": "Q",
        "s": "S",
        "sq": "SQ",
        "": "R",  # Default
    }

    while True:
        session_input = input("\nEnter session type (R/Q/S/SQ, default: R): ").strip().lower()
        if session_input in session_map:
            session_type = session_map[session_input]
            break
        else:
            print("❌ Invalid session type. Choose R, Q, S, or SQ.")

    session_names = {
        "R": "Race",
        "Q": "Qualifying",
        "S": "Sprint",
        "SQ": "Sprint Qualifying",
    }

    print(f"\n✅ Selected session: {session_names[session_type]}\n")

    # Final confirmation
    print("=" * 80)
    print("📋 SELECTION SUMMARY:")
    print(f"   Year:          {year}")
    print(f"   Round:         {round_number} - {event_name}")
    print(f"   Date:          {event_date}")
    print(f"   Session:       {session_names[session_type]}")
    print("=" * 80 + "\n")

    confirm = input("Proceed? (Y/n): ").strip().lower()
    if confirm == "n":
        print("\n🔄 Restarting selection...\n")
        return interactive_session_selector()

    print("\n🚀 Loading session...\n")
    return year, round_number, session_type


def quick_select_latest_race() -> tuple[int, int, SessionType]:
    """
    Quick select the most recent race.

    Returns:
        Tuple of (year, round_number, session_type)
    """
    import datetime

    current_year = datetime.datetime.now().year

    # Try current year first
    for year in [current_year, current_year - 1]:
        try:
            schedule = fastf1.get_event_schedule(year, include_testing=False)
            # Find most recent completed event
            now = datetime.datetime.now()
            completed = schedule[schedule["EventDate"] < now]

            if len(completed) > 0:
                latest = completed.iloc[-1]
                round_number = int(latest["RoundNumber"])
                event_name = latest["EventName"]

                print(f"🏁 Latest race: {year} Round {round_number} - {event_name}")
                session_type: SessionType = "R"
                return year, round_number, session_type

        except Exception as e:
            logger.warning(f"Could not fetch schedule for {year}: {e}")
            continue

    # Fallback
    print("⚠️ Could not determine latest race. Using default.")
    return 2024, 1, "R"
