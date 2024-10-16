import requests
import re
from datetime import datetime

API_URL = "https://aoe4world.com/api/v0/games?profile_ids=17272020"
GAMES_FILE = "content/games.md"
TITUS_PROFILE_ID = 17272020

def get_existing_games():
    with open(GAMES_FILE, 'r') as f:
        content = f.read()
    table_match = re.search(r'\|.*?\|(.*?)\n\|[-\s|]+\n(.*)', content, re.DOTALL)
    if table_match:
        return {game.split('|')[0].strip(): game.strip() for game in table_match.group(2).strip().split('\n')}
    return {}

def update_games_file(games):
    with open(GAMES_FILE, 'r') as f:
        content = f.readlines()

    table_start = content.index("| Date and Time | Result | Matchup | Rating Change | MMR Difference |\n")
    
    # Find the end of the table or use the end of the file
    table_end = next((i for i, line in enumerate(content[table_start+2:], start=table_start+2) if line.strip() and not line.startswith('|')), len(content))

    new_table = content[:table_start + 2] + [f"{game}\n" for game in games.values()] + content[table_end:]

    with open(GAMES_FILE, 'w') as f:
        f.writelines(new_table)

def main():
    response = requests.get(API_URL)
    api_games = response.json()['games']

    existing_games = get_existing_games()
    updated_games = {}

    for game in api_games:
        date_time = datetime.fromisoformat(game['started_at'].replace('Z', '+00:00'))
        formatted_date = date_time.strftime("%Y-%m-%d %H:%M")

        player = next(p for team in game['teams'] for p in team if p['player']['profile_id'] == TITUS_PROFILE_ID)
        opponent = next(p for team in game['teams'] for p in team if p['player']['profile_id'] != TITUS_PROFILE_ID)

        result = "Win" if player['player']['result'] == "win" else "Loss"
        matchup = f"{player['player']['civilization'].replace('_', ' ').title()} vs {opponent['player']['civilization'].replace('_', ' ').title()}"
        rating_diff = player['player']['rating_diff']
        rating_change = f"+{rating_diff}" if rating_diff and rating_diff > 0 else str(rating_diff) if rating_diff else "N/A"
        
        # Calculate MMR difference
        titus_mmr = player['player'].get('rating')
        opponent_mmr = opponent['player'].get('rating')
        mmr_diff = opponent_mmr - titus_mmr if titus_mmr is not None and opponent_mmr is not None else None
        mmr_diff_str = str(mmr_diff) if mmr_diff is not None else 'N/A'

        new_game_entry = f"| {formatted_date} | {result} | {matchup} | {rating_change} | {mmr_diff_str} |"

        if formatted_date in existing_games:
            existing_entry = existing_games[formatted_date]
            existing_fields = existing_entry.split('|')
            new_fields = new_game_entry.split('|')
            
            # Check if any field has changed
            if any(existing_fields[i].strip() != new_fields[i].strip() for i in range(1, 6)):
                updated_games[formatted_date] = new_game_entry
        else:
            updated_games[formatted_date] = new_game_entry

    if updated_games:
        all_games = {**existing_games, **updated_games}
        sorted_games = dict(sorted(all_games.items(), reverse=True))
        update_games_file(sorted_games)
    else:
        print("No updates needed.")

if __name__ == "__main__":
    main()
