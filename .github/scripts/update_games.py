import requests
import re
from datetime import datetime
from bs4 import BeautifulSoup

API_URL = "https://aoe4world.com/api/v0/games?profile_ids=17272020"
GAMES_FILE = "content/games.md"
HALL_OF_FAME_FILE = "content/halloffame.md"
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
        rows = table_match.group(2).strip().split('\n')
        for row in rows:
            if row.strip():
                cells = [cell.strip() for cell in row.split('|')[1:-1]]  # Split and remove empty edges
                if len(cells) >= 5:
                    date = cells[0]
                    matchup = cells[2]
                    opponent_name = matchup.split('(')[-1].strip(')')
                    key = f"{date}_{opponent_name}"
                    games[key] = '|' + '|'.join(cells) + '|'
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
    
    # Read the full games.md content to get the linked versions of games
    with open(GAMES_FILE, 'r', encoding='utf-8') as f:
        games_content = f.read()
    
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
                    # Find the full line with links from games.md
                    date_pattern = re.escape(date)
                    matchup_pattern = re.escape(matchup)
                    full_line_pattern = f"\\|[^|]*{date_pattern}[^|]*\\|[^|]*{result}[^|]*\\|[^|]*{matchup_pattern}[^|]*\\|[^|]*{opponent_rating}[^|]*\\|[^|]*\\|"
                    full_line_match = re.search(full_line_pattern, games_content)
                    
                    if full_line_match:
                        linked_game = full_line_match.group(0)
                    else:
                        linked_game = game
                        
                    if "Win" in result:
                        best_wins.append((rating, parse_date(date), linked_game))
                    elif "Loss" in result:
                        worst_losses.append((rating, parse_date(date), linked_game))
                    seen_games.add(game_key)
                except ValueError:
                    print(f"Debug: ValueError for game - {game}")
                    continue

    # Sort and get top 5 unique wins and bottom 5 unique losses
    best_wins = sorted(best_wins, key=lambda x: (x[0], x[1]), reverse=True)[:5]
    worst_losses = sorted(worst_losses, key=lambda x: (x[0], x[1]))[:5]

    # Read existing frontmatter if file exists
    frontmatter = """---
title: "Hall of Fame"
url: /halloffame/
description: ""
tags: [streams, twitch, youtube]
featured_image: "/images/halloffame.webp"
categories: Streams
comment: true
draft: false
---\n\n"""

    best_wins_content = (f"# Hall of Fame\n\n"
                        f"### Best Wins\n\n"
                        "| Date and Time | Result | Matchup | Opponent Rating | MMR Difference |\n"
                        "|---------------|--------|---------|-----------------|----------------|\n" + 
                        "\n".join(game for _, _, game in best_wins))
    
    worst_losses_content = (f"\n\n### Worst Losses\n\n"
                            "| Date and Time | Result | Matchup | Opponent Rating | MMR Difference |\n"
                            "|---------------|--------|---------|-----------------|----------------|\n" + 
                            "\n".join(game for _, _, game in worst_losses))

    with open(HALL_OF_FAME_FILE, 'w', encoding='utf-8') as f:
        f.write(frontmatter + best_wins_content + worst_losses_content)

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

    # Always read fresh data from games.md for hall of fame
    all_games = get_existing_games()
    update_best_wins_and_worst_losses(all_games)

if __name__ == "__main__":
    main()
