import requests
import re
from datetime import datetime

API_URL = "https://aoe4world.com/api/v0/games?profile_ids=17272020"
GAMES_FILE = "content/games.md"
TITUS_PROFILE_ID = 17272020

def get_existing_games():
    with open(GAMES_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    table_match = re.search(r'\|.*?\|(.*?)\n\|[-\s|]+\n(.*)', content, re.DOTALL)
    if table_match:
        return {game.split('|')[0].strip(): game.strip() for game in table_match.group(2).strip().split('\n')}
    return {}

def update_games_file(new_games):
    with open(GAMES_FILE, 'r', encoding='utf-8') as f:
        content = f.readlines()

    table_start = content.index("| Date and Time | Result | Matchup | Opponent Rating | MMR Difference |\n")
    table_end = next((i for i, line in enumerate(content[table_start+2:], start=table_start+2) if line.strip() and not line.startswith('|')), len(content))

    # Extract existing games
    existing_games = [line.strip() for line in content[table_start+2:table_end] if line.strip()]
    
    # Combine existing games with new games
    all_games = existing_games + list(new_games.values())
    
    # Remove duplicates while preserving order
    unique_games = []
    seen = set()
    for game in reversed(all_games):
        key = game.split('|')[1].strip()  # Use date as the unique key
        if key not in seen:
            unique_games.append(game)
            seen.add(key)
    unique_games.reverse()

    # Update the file content
    new_table = content[:table_start + 2] + [f"{game}\n" for game in unique_games] + content[table_end:]

    with open(GAMES_FILE, 'w', encoding='utf-8') as f:
        f.writelines(new_table)

def get_best_wins(games):
    best_wins = []
    for game in games.values():
        fields = game.split('|')
        if len(fields) >= 5 and "Win" in game:
            best_wins.append(game)
    return best_wins

def get_worst_losses(games):
    worst_losses = []
    for game in games.values():
        fields = game.split('|')
        if len(fields) >= 5 and "Loss" in game:
            worst_losses.append(game)
    return worst_losses

def update_best_wins_and_worst_losses(games):
    best_wins = []
    worst_losses = []
    
    seen_games = set()

    for game in games.values():
        fields = game.split('|')
        if len(fields) >= 5:
            result = fields[2].strip()
            opponent_rating = fields[4].strip()
            game_key = (fields[1].strip(), fields[3].strip())
            if opponent_rating != 'N/A' and game_key not in seen_games:
                try:
                    rating = int(opponent_rating)
                    if "Win" in result:
                        best_wins.append((rating, game))
                    elif "Loss" in result:
                        worst_losses.append((rating, game))
                    seen_games.add(game_key)
                except ValueError:
                    continue

    # Sort and get top 5 unique wins and bottom 5 unique losses
    best_wins = sorted(best_wins, key=lambda x: x[0], reverse=True)[:5]
    worst_losses = sorted(worst_losses, key=lambda x: x[0])[:5]

    with open(GAMES_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    best_wins_header = "### Best Wins"
    worst_losses_header = "### Worst Losses"

    best_wins_content = (f"{best_wins_header}\n\n"
                         "| Date and Time | Result | Matchup | Opponent Rating | MMR Difference |\n"
                         "|---------------|--------|---------|-----------------|----------------|\n" + 
                         "\n".join(game for _, game in best_wins))
    
    worst_losses_content = (f"{worst_losses_header}\n\n"
                            "| Date and Time | Result | Matchup | Opponent Rating | MMR Difference |\n"
                            "|---------------|--------|---------|-----------------|----------------|\n" + 
                            "\n".join(game for _, game in worst_losses))

    # Replace or append the sections
    if best_wins_header in content and worst_losses_header in content:
        best_wins_start = content.index(best_wins_header)
        worst_losses_start = content.index(worst_losses_header)
        if best_wins_start < worst_losses_start:
            new_content = (
                content[:best_wins_start] + 
                best_wins_content + "\n\n" +
                worst_losses_content
            )
        else:
            new_content = (
                content[:worst_losses_start] + 
                worst_losses_content + "\n\n" +
                best_wins_content
            )
    else:
        new_content = content + "\n\n" + best_wins_content + "\n\n" + worst_losses_content

    with open(GAMES_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content)

def main():
    response = requests.get(API_URL)
    api_games = response.json()['games']

    existing_games = get_existing_games()
    new_games = {}

    for game in api_games:
        # Check if it's a 1v1 game
        if sum(len(team) for team in game['teams']) != 2:
            continue  # Skip this game if it's not a 1v1

        date_time = datetime.fromisoformat(game['started_at'].replace('Z', '+00:00'))
        formatted_date = date_time.strftime("%Y-%m-%d %H:%M")

        player = next(p for team in game['teams'] for p in team if p['player']['profile_id'] == TITUS_PROFILE_ID)
        opponent = next(p for team in game['teams'] for p in team if p['player']['profile_id'] != TITUS_PROFILE_ID)

        result = "Win" if player['player']['result'] == "win" else "Loss"
        opponent_name = opponent['player']['name']
        matchup = f"{player['player']['civilization'].replace('_', ' ').title()} vs {opponent['player']['civilization'].replace('_', ' ').title()} ({opponent_name})"
        
        # Get opponent rating
        opponent_rating = opponent['player'].get('rating', 'N/A')
        
        # Calculate MMR difference
        titus_mmr = player['player'].get('rating')
        opponent_mmr = opponent['player'].get('rating')
        mmr_diff = opponent_mmr - titus_mmr if titus_mmr is not None and opponent_mmr is not None else None
        mmr_diff_str = str(mmr_diff) if mmr_diff is not None else 'N/A'

        new_game_entry = f"| {formatted_date} | {result} | {matchup} | {opponent_rating} | {mmr_diff_str} |"
        unique_key = formatted_date

        if unique_key not in existing_games:
            new_games[unique_key] = new_game_entry

    if new_games:
        update_games_file(new_games)

        # Add a line break after updating the main games table
        with open(GAMES_FILE, 'a', encoding='utf-8') as f:
            f.write('\n')

        # Update best wins and worst losses in the markdown file
        all_games = {**existing_games, **new_games}
        update_best_wins_and_worst_losses(all_games)
    else:
        print("No new games to add.")

if __name__ == "__main__":
    main()
