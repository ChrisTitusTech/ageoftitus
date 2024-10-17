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

def update_games_file(games):
    with open(GAMES_FILE, 'r', encoding='utf-8') as f:
        content = f.readlines()

    table_start = content.index("| Date and Time | Result | Matchup | Rating Change | MMR Difference |\n")
    
    table_end = next((i for i, line in enumerate(content[table_start+2:], start=table_start+2) if line.strip() and not line.startswith('|')), len(content))

    new_table = content[:table_start + 2] + [f"{game}\n" for game in games.values()] + content[table_end:]

    with open(GAMES_FILE, 'w', encoding='utf-8') as f:
        f.writelines(new_table)

def get_best_wins(games):
    best_wins = []
    for game in games.values():
        fields = game.split('|')
        if len(fields) >= 5 and "Win" in game:
            mmr_diff = fields[-2].strip()
            if mmr_diff != 'N/A':
                try:
                    if int(mmr_diff) > 100:
                        best_wins.append(game)
                except ValueError:
                    continue  # Skip this game if MMR difference can't be converted to int
    return best_wins

def get_worst_losses(games):
    worst_losses = []
    for game in games.values():
        fields = game.split('|')
        if len(fields) >= 5 and "Loss" in game:
            mmr_diff = fields[-2].strip()
            if mmr_diff != 'N/A':
                try:
                    if int(mmr_diff) <= -100:
                        worst_losses.append(game)
                except ValueError:
                    continue  # Skip this game if MMR difference can't be converted to int
    return worst_losses

def update_best_wins_and_worst_losses(best_wins, worst_losses):
    with open(GAMES_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    best_wins_header = "### Best Wins (MMR Difference > 100)"
    worst_losses_header = "### Worst Losses (MMR Difference <= -100)"

    if best_wins_header not in content:
        # Add Best Wins section if it doesn't exist
        content += f"\n\n{best_wins_header}\n\n| Date and Time | Result | Matchup | Rating Change | MMR Difference |\n|---------------|--------|---------|---------------|----------------|\n"

    if worst_losses_header not in content:
        # Add Worst Losses section if it doesn't exist
        content += f"\n\n{worst_losses_header}\n\n| Date and Time | Result | Matchup | Rating Change | MMR Difference |\n|---------------|--------|---------|---------------|----------------|\n"

    best_wins_start = content.index(best_wins_header)
    worst_losses_start = content.index(worst_losses_header)

    # Find the end of the existing tables
    best_wins_end = content.find("\n\n", best_wins_start)
    worst_losses_end = content.find("\n\n", worst_losses_start)
    if worst_losses_end == -1:  # If it's the last section
        worst_losses_end = len(content)

    # Extract existing entries
    existing_best_wins = set(line.strip() for line in content[best_wins_start:best_wins_end].split('\n')[3:] if line.strip() and line.startswith('|'))
    existing_worst_losses = set(line.strip() for line in content[worst_losses_start:worst_losses_end].split('\n')[3:] if line.strip() and line.startswith('|'))

    def sort_key(entry):
        mmr_diff = entry.split('|')[-2].strip()
        return int(mmr_diff) if mmr_diff != 'N/A' else -float('inf')

    # Combine and sort entries
    updated_best_wins = sorted(existing_best_wins.union(best_wins), key=sort_key, reverse=True)
    updated_worst_losses = sorted(existing_worst_losses.union(worst_losses), key=sort_key, reverse=True)

    # Prepare new content
    best_wins_content = (f"{best_wins_header}\n\n"
                         "| Date and Time | Result | Matchup | Rating Change | MMR Difference |\n"
                         "|---------------|--------|---------|---------------|----------------|\n" + 
                         "\n".join(updated_best_wins))
    
    worst_losses_content = (f"{worst_losses_header}\n\n"
                            "| Date and Time | Result | Matchup | Rating Change | MMR Difference |\n"
                            "|---------------|--------|---------|---------------|----------------|\n" + 
                            "\n".join(updated_worst_losses))

    # Replace the old sections with new content or append if they don't exist
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

    with open(GAMES_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content)

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
        opponent_name = opponent['player']['name']  # Assuming 'name' is the key for the opponent's name
        matchup = f"{player['player']['civilization'].replace('_', ' ').title()} vs {opponent['player']['civilization'].replace('_', ' ').title()} ({opponent_name})"
        rating_diff = player['player']['rating_diff']
        rating_change = f"+{rating_diff}" if rating_diff and rating_diff > 0 else str(rating_diff) if rating_diff else "N/A"
        
        # Calculate MMR difference
        titus_mmr = player['player'].get('rating')
        opponent_mmr = opponent['player'].get('rating')
        mmr_diff = opponent_mmr - titus_mmr if titus_mmr is not None and opponent_mmr is not None else None
        mmr_diff_str = str(mmr_diff) if mmr_diff is not None else 'N/A'

        new_game_entry = f"| {formatted_date} | {result} | {matchup} | {rating_change} | {mmr_diff_str} |"

        # Use a unique key combining date and opponent name to avoid duplicates
        unique_key = f"{formatted_date}_{opponent_name}"

        if unique_key in existing_games:
            existing_entry = existing_games[unique_key]
            existing_fields = existing_entry.split('|')
            new_fields = new_game_entry.split('|')
            
            # Check if any field has changed
            if any(existing_fields[i].strip() != new_fields[i].strip() for i in range(1, 6)):
                updated_games[unique_key] = new_game_entry
        else:
            updated_games[unique_key] = new_game_entry

    if updated_games:
        all_games = {**existing_games, **updated_games}
        sorted_games = dict(sorted(all_games.items(), reverse=True))
        update_games_file(sorted_games)

        # Add a line break after updating the main games table
        with open(GAMES_FILE, 'a', encoding='utf-8') as f:
            f.write('\n')

        # Get best wins and worst losses
        best_wins = get_best_wins(sorted_games)
        worst_losses = get_worst_losses(sorted_games)

        # Update best wins and worst losses in the markdown file
        update_best_wins_and_worst_losses(best_wins, worst_losses)
    else:
        print("No updates needed.")

if __name__ == "__main__":
    main()
