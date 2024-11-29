import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Replace with your Chess.com username
USERNAME = input("your chess.com username: ")

def fetch_archives(username):
    """Fetch all game archive URLs for the user."""
    url = f"https://api.chess.com/pub/player/{username}/games/archives"
    headers = {
        'User-Agent': 'MyAppName/1.0 (Contact: your_email@example.com)'
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get("archives", [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching archives: {e}")
        return []

def fetch_games(archive_url):
    """Fetch games from a specific archive."""
    headers = {
        'User-Agent': 'MyAppName/1.0 (Contact: your_email@example.com)'
    }
    try:
        response = requests.get(archive_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get("games", [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching games from {archive_url}: {e}")
        return []

def clean_opening_name(opening):
    """Clean and format the opening name."""
    if "https://www.chess.com/openings/" in opening:
        return opening.split("/")[-1].replace("-", " ").capitalize()
    return opening

def extract_opening_stats(games, color):
    """Extract opening stats based on whether the user played as white or black."""
    stats = {}
    for game in games:
        try:
            # Filter games based on color
            if color == "white" and game["white"]["username"].lower() != USERNAME.lower():
                continue
            if color == "black" and game["black"]["username"].lower() != USERNAME.lower():
                continue

            pgn = game.get("pgn", "")
            opening_line = next((line for line in pgn.split("\n") if line.startswith("[Opening ")), None)
            if not opening_line:
                eco_url = game.get("eco_url", "")
                opening = clean_opening_name(eco_url if eco_url else game.get("eco", "Undefined"))
            else:
                opening = clean_opening_name(opening_line.split('"')[1])

            # Skip undefined openings
            if opening.lower() == "undefined":
                continue

            result_line = next((line for line in pgn.split("\n") if line.startswith("[Result ")), None)
            if not result_line:
                continue
            result = result_line.split('"')[1]

            if opening not in stats:
                stats[opening] = {"Win": 0, "Loss": 0, "Draw": 0}

            if (color == "white" and result == "1-0") or (color == "black" and result == "0-1"):
                stats[opening]["Win"] += 1
            elif (color == "white" and result == "0-1") or (color == "black" and result == "1-0"):
                stats[opening]["Loss"] += 1
            elif result == "1/2-1/2":
                stats[opening]["Draw"] += 1
        except Exception as e:
            print(f"Error processing game: {e}")
    return stats

def calculate_percentages(stats):
    """Calculate win/loss/draw percentages for each opening."""
    percentages = []
    for opening, results in stats.items():
        total_games = sum(results.values())
        if total_games > 0:
            win_pct = (results["Win"] / total_games) * 100
            loss_pct = (results["Loss"] / total_games) * 100
            draw_pct = (results["Draw"] / total_games) * 100
            percentages.append({
                "Opening": opening,
                "Win %": win_pct,
                "Loss %": loss_pct,
                "Draw %": draw_pct,
                "Total Games": total_games,
                "Success Ratio": (results["Win"] + results["Draw"]) / max(results["Loss"], 1)  # Avoid division by zero
            })
    return pd.DataFrame(percentages) if percentages else pd.DataFrame()

def create_graph(opening_percentages, output_file, title):
    """Create and save the stacked bar graph."""
    if opening_percentages.empty:
        print(f"No valid data to plot for {title}.")
        return

    # Sort and focus on top 10 most-used openings
    opening_percentages = opening_percentages.sort_values(by="Total Games", ascending=False).head(10)

    # Find the most successful opening
    most_successful_opening = opening_percentages.sort_values(by="Success Ratio", ascending=False).iloc[0]["Opening"]

    # Prepare data for stacked bar graph
    df_melted = opening_percentages.melt(
        id_vars=["Opening"],
        value_vars=["Win %", "Loss %", "Draw %"],
        var_name="Result",
        value_name="Percentage"
    )

    # Custom colors for the bars
    colors = {"Win %": "#800080", "Loss %": "#FFA500", "Draw %": "#00FF00"}

    # Create the plot
    plt.figure(figsize=(14, 8))
    sns.set_theme(style="darkgrid", rc={"axes.facecolor": "black", "grid.color": "gray"})
    ax = sns.barplot(
        x="Opening",
        y="Percentage",
        hue="Result",
        data=df_melted,
        palette=colors,
        edgecolor="black"
    )

    # Add a crown to the most successful opening
    for i, opening in enumerate(opening_percentages["Opening"]):
        if opening == most_successful_opening:
            ax.text(
                i,
                max(df_melted[df_melted["Opening"] == opening]["Percentage"]) + 5,
                "👑",
                ha="center",
                va="bottom",
                fontsize=16,
                color="gold"
            )

    # Customize the graph
    ax.set_title(title, color="black", fontsize=16)
    ax.set_xlabel("Opening", color="black")  # Changed to black
    ax.set_ylabel("Percentage", color="black")  # Changed to black
    ax.tick_params(axis="x", colors="black", rotation=45)  # Changed to black
    ax.tick_params(axis="y", colors="black")  # Changed to black
    ax.legend(title="Result", loc="upper left", facecolor="black", edgecolor="gray", labelcolor="white")

    # Save the plot as an image file
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    print(f"Graph saved as {output_file}. You can download it to view.")

# Fetch and process game data
archives = fetch_archives(USERNAME)
all_games = []
for archive in archives:
    all_games.extend(fetch_games(archive))

# Extract stats for games where the user played as white
white_opening_stats = extract_opening_stats(all_games, color="white")
white_percentages = calculate_percentages(white_opening_stats)
create_graph(white_percentages, "as_white.png", "Win/Loss/Draw Percentages for Top 10 Openings (As White)")

# Extract stats for games where the user played as black
black_opening_stats = extract_opening_stats(all_games, color="black")
black_percentages = calculate_percentages(black_opening_stats)
create_graph(black_percentages, "as_black.png", "Win/Loss/Draw Percentages for Top 10 Openings (As Black)")