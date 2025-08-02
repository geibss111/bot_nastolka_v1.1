
from parser import parse_html_content

with open("up_games.html", "r", encoding="utf-8") as f:
    html_content = f.read()
    games = parse_html_content(html_content)
    for game in games:
        print(game)


