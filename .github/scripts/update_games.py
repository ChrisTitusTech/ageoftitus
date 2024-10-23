import requests
import re
from datetime import datetime
from bs4 import BeautifulSoup

API_URL = "https://aoe4world.com/api/v0/games?profile_ids=17272020"
GAMES_FILE = "content/games.md"
TITUS_PROFILE_ID = 17272020

def parse_date(date_string):
    return datetime.strptime(date_string.strip(), "%Y-%m-%d %H:%M")

def remove_markdown_links(text):
    return re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

def get_existing_games():
    with open(GAMES_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove markdown links from the content
    content_without_links = remove_markdown_links(content)
    
    table_match = re.search(r'\|.*?\|(.*?)\n\|[-\s|]+\n(.*)', content_without_links, re.DOTALL)
    if table_match:
        games = {}
        soup = BeautifulSoup(table_match.group(2), 'html.parser')
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 5:
                date = cells[0].get_text(strip=True)
                matchup = cells[2].get_text(strip=True)
                opponent_name = matchup.split('(')[-1].strip(')')  # Extract opponent name from matchup
                key = f"{date}_{opponent_name}"
                games[key] = '|' + '|'.join(cell.get_text(strip=True) for cell in cells) + '|'
        return games
    return {}

def update_games_file(new_games):
    with open(GAMES_FILE, 'r', encoding='utf-8') as f:
        content = f.readlines()

    table_start = content.index("| Date and Time | Result | Matchup | Opponent Rating | MMR Difference |\n")
    table_end = next((i for i, line in enumerate(content[table_start+2:], start=table_start+2) if line.strip() and not line.startswith('|')), len(content))

    # Extract existing games
    existing_games = [line.strip() for line in content[table_start+2:table_end] if line.strip()]
    
    # Create a set of existing game dates to check for duplicates
    existing_game_dates = set()
    for game in existing_games:
        date = game.split('|')[1].strip()
        # Handle both linked and unlinked dates
        if date.startswith('['):
            date = date.split(']')[0][1:]  # Extract date from [date](link)
        existing_game_dates.add(date)
    
    # Add new games to the beginning of the list, avoiding duplicates
    all_games = existing_games.copy()  # Start with existing games
    for game in new_games.values():
        date = game.split('|')[1].strip()
        if date not in existing_game_dates:
            all_games.insert(0, game)  # Insert new games at the beginning
            existing_game_dates.add(date)
    
    # Update the file content
    new_table = content[:table_start + 2] + [f"{game}\n" for game in all_games] + content[table_end:]

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
            date = fields[1].strip()
            result = fields[2].strip()
            matchup = fields[3].strip()
            opponent_rating = fields[4].strip()
            game_key = (date, matchup)
            if opponent_rating != 'N/A' and game_key not in seen_games:
                try:
                    rating = int(opponent_rating)
                    if "Win" in result:
                        best_wins.append((rating, parse_date(date), game))
                    elif "Loss" in result:
                        worst_losses.append((rating, parse_date(date), game))
                    seen_games.add(game_key)
                except ValueError:
                    print(f"Debug: ValueError for game - {game}")  # Debug print
                    continue

    # Sort and get top 5 unique wins and bottom 5 unique losses
    best_wins = sorted(best_wins, key=lambda x: (x[0], x[1]), reverse=True)[:5]
    worst_losses = sorted(worst_losses, key=lambda x: (x[0], x[1]))[:5]

    print("Debug: Top 5 best wins:")  # Debug print
    for rating, date, game in best_wins:
        print(f"Rating: {rating}, Date: {date}, Game: {game}")

    print("\nDebug: Top 5 worst losses:")  # Debug print
    for rating, date, game in worst_losses:
        print(f"Rating: {rating}, Date: {date}, Game: {game}")

    with open(GAMES_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    best_wins_header = "### Best Wins"
    worst_losses_header = "### Worst Losses"

    best_wins_content = (f"{best_wins_header}\n\n"
                         "| Date and Time | Result | Matchup | Opponent Rating | MMR Difference |\n"
                         "|---------------|--------|---------|-----------------|----------------|\n" + 
                         "\n".join(game for _, _, game in best_wins))
    
    worst_losses_content = (f"{worst_losses_header}\n\n"
                            "| Date and Time | Result | Matchup | Opponent Rating | MMR Difference |\n"
                            "|---------------|--------|---------|-----------------|----------------|\n" + 
                            "\n".join(game for _, _, game in worst_losses))

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

    print(f"Debug: Found {len(api_games)} games from API")
    print(f"Debug: Found {len(existing_games)} existing games")

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
        
        opponent_rating = opponent['player'].get('rating', 'N/A')
        
        titus_mmr = player['player'].get('rating')
        opponent_mmr = opponent['player'].get('rating')
        mmr_diff = opponent_mmr - titus_mmr if titus_mmr is not None and opponent_mmr is not None else None
        mmr_diff_str = str(mmr_diff) if mmr_diff is not None else 'N/A'

        new_game_entry = f"| {formatted_date} | {result} | {matchup} | {opponent_rating} | {mmr_diff_str} |"
        unique_key = f"{formatted_date}_{opponent_name}"

        if unique_key not in existing_games:
            new_games[unique_key] = new_game_entry

    print(f"Debug: Found {len(new_games)} new games to add")

    if new_games:
        print("Debug: Updating games file")
        update_games_file(new_games)

        # Add a line break after updating the main games table
        with open(GAMES_FILE, 'a', encoding='utf-8') as f:
            f.write('\n')

        # Update best wins and worst losses in the markdown file
        all_games = {**existing_games, **new_games}
        update_best_wins_and_worst_losses(all_games)
    else:
        print("No new games to add.")
        # Even if no new games, update best wins and worst losses
        update_best_wins_and_worst_losses(existing_games)

if __name__ == "__main__":
    main()
