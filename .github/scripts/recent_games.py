import requests
from datetime import datetime, timedelta
import pytz
import re
from requests.exceptions import RequestException
import time

API_URL = "https://aoe4world.com/api/v0/games?profile_ids=17272020"
OUTPUT_FILE = "recent_games.txt"
TITUS_PROFILE_ID = 17272020
AOE4_WORLD_URL = "https://aoe4world.com/players/17272020-TitusMaximus/games"

# Add new constant for session gap
SESSION_GAP_HOURS = 2
LOOKBACK_HOURS = 24  # Changed from 12 to 24 hours

def get_twitch_links(page_source, num_games):
    print("Extracting Twitch links...")
    twitch_pattern = r'href="(https://www\.twitch\.tv/videos/\d+\?t=\d+s)"'
    matches = re.findall(twitch_pattern, page_source)
    return matches[:num_games]

def format_timestamp(twitch_link):
    match = re.search(r't=(\d+)s', twitch_link)
    if match:
        seconds = int(match.group(1))
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return "00:00:00"

def get_aoe4world_page(max_retries=3, delay=5):
    print("Fetching AoE4 World page...")
    for attempt in range(max_retries):
        try:
            response = requests.get(AOE4_WORLD_URL, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            response.raise_for_status()  # Raises an HTTPError for bad responses
            content = response.text
            if len(content) > 1000:  # Arbitrary check to ensure we got a full page
                print(f"Fetched AoE4 World page, length: {len(content)} characters")
                return content
            else:
                print(f"Attempt {attempt + 1}: Received incomplete content. Retrying...")
        except RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}")
        
        if attempt < max_retries - 1:
            print(f"Waiting {delay} seconds before retrying...")
            time.sleep(delay)
    
    raise Exception("Failed to fetch AoE4 World page after multiple attempts")

def main():
    print("Fetching games from API...")
    response = requests.get(API_URL)
    api_games = response.json()['games']
    print(f"Found {len(api_games)} games in API response")

    current_time = datetime.now(pytz.UTC)
    twenty_four_hours_ago = current_time - timedelta(hours=LOOKBACK_HOURS)
    print(f"Current time: {current_time}, Twenty four hours ago: {twenty_four_hours_ago}")

    # Modified game processing to include team games
    all_games = []
    print("Processing games...")
    for game in api_games:
        game_time = datetime.fromisoformat(game['updated_at'].replace('Z', '+00:00'))
        
        if game_time < twenty_four_hours_ago:
            print("Game is older than 24 hours, stopping processing")
            break

        # Remove the 1v1 check to include team games
        player = next(p for team in game['teams'] for p in team if p['player']['profile_id'] == TITUS_PROFILE_ID)
        # Find all opponents
        opponents = [p for team in game['teams'] for p in team if p['player']['profile_id'] != TITUS_PROFILE_ID]
        
        result = "Win" if player['player']['result'] == "win" else "Loss"
        # Format opponent names based on number of players
        if len(opponents) == 1:
            opponent_info = f"({opponents[0]['player']['name']})"
        else:
            team_size = len(game['teams'][0])  # Get size of first team
            opponent_info = f"({team_size}v{team_size} Team Game)"

        matchup = f"{player['player']['civilization'].replace('_', ' ').title()} {opponent_info}"
        
        all_games.append((game_time, result, matchup))
        print(f"Added game: {game_time} {result} {matchup}")

    # Find the last session of games
    recent_games = []
    if all_games:
        last_game_time = all_games[0][0]
        recent_games = [(all_games[0])]
        
        for game in all_games[1:]:
            time_diff = last_game_time - game[0]
            if time_diff.total_seconds() / 3600 <= SESSION_GAP_HOURS:
                recent_games.append(game)
                last_game_time = game[0]
            else:
                break

    print(f"Found {len(recent_games)} games in the last session")

    try:
        aoe4world_page = get_aoe4world_page()
        print(f"Fetched AoE4 World page, length: {len(aoe4world_page)} characters")

        twitch_links = get_twitch_links(aoe4world_page, len(recent_games))
        print(f"Found {len(twitch_links)} Twitch links")

        final_games = []
        for (game_time, result, matchup), twitch_link in zip(recent_games, twitch_links):
            formatted_timestamp = format_timestamp(twitch_link)
            final_games.append((formatted_timestamp, f"{formatted_timestamp} {result} {matchup}"))

        # Sort by timestamp instead of game_time
        final_games.sort(key=lambda x: x[0])

        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            if final_games:
                f.write("Recent games (last 12 hours):\n\n")
                f.write("Chapters:\n")
                f.write("00:00:00 Intro\n")  # Add the Intro line
                for _, game_info in final_games:
                    f.write(f"{game_info}\n")
            else:
                f.write("No games played in the last 12 hours.")

        print(f"Wrote results to {OUTPUT_FILE}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
