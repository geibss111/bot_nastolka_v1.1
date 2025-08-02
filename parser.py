# C:\Users\Дианка\PycharmProjects\pythonProject4\bot_tennis4_beta\parser.py
import requests
from bs4 import BeautifulSoup
import logging
import re

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def parse_html_content(html_content):
    logger.info(f"HTML content length: {len(html_content)} characters")

    soup = BeautifulSoup(html_content, 'html.parser')
    games = []

    # Ищем все блоки с предстоящими играми по более простому селектору
    # Ищем div с классом row, который содержит информацию об игре
    game_containers = soup.find_all('div', class_='row')

    logger.info(f"Found {len(game_containers)} row containers")

    for container in game_containers:
        try:
            # Проверяем, содержит ли контейнер информацию об игроках
            player_links = container.find_all('a', class_='name')
            if len(player_links) < 2:
                continue

            # Извлекаем имена игроков с корректным форматированием
            def format_player_name(player_link):
                # Ищем span элементы внутри ссылки
                spans = player_link.find_all('span')
                if len(spans) >= 1:
                    first_name = spans[0].get_text(strip=True)
                    # Получаем оставшийся текст после span элементов
                    full_text = player_link.get_text()
                    # Убираем имя и лишние пробелы
                    last_name = full_text.replace(first_name, '').strip()
                    # Объединяем с пробелом
                    return f"{first_name} {last_name}".strip()
                else:
                    # Если нет span, просто очищаем текст
                    return player_link.get_text(strip=True).replace('\n', ' ').replace('  ', ' ')

            player1 = format_player_name(player_links[0])
            player2 = format_player_name(player_links[1])

            # --- ИЩЕМ СЧЕТ ЛИЧНЫХ ВСТРЕЧ ПРАВИЛЬНО ---
            # Ищем div с текстом "счет последних личных встреч"
            personal_score_label = container.find('div',
                                                  string=re.compile(r'счет последних личных встреч', re.IGNORECASE))

            if not personal_score_label:
                # logger.debug(f"Personal score label not found for {player1} vs {player2}")
                continue

            score_text = "N/A"
            total_score = 0
            # --- Переменные для индивидуальных побед ---
            wins_player1 = 0
            wins_player2 = 0
            # ------------------------------------------------

            # Счет личных встреч находится в div class="game-score", который должен быть
            # в том же родительском элементе, что и метка
            parent_of_label = personal_score_label.parent
            if parent_of_label:
                game_score_div = parent_of_label.find('div', class_='game-score')
                if game_score_div:
                    score_text_raw = game_score_div.get_text(strip=True)
                    # logger.debug(f"Found raw score text: '{score_text_raw}'")
                    # Проверяем формат X:Y
                    score_match = re.match(r'(\d+)\s*:\s*(\d+)', score_text_raw)
                    if score_match:
                        try:
                            player1_score = int(score_match.group(1))  # Победы Игрока 1
                            player2_score = int(score_match.group(2))  # Победы Игрока 2
                            score_text = f"{player1_score} : {player2_score}"
                            total_score = player1_score + player2_score
                            # --- Сохраняем индивидуальные победы ---
                            wins_player1 = player1_score
                            wins_player2 = player2_score
                            # -----------------------------------------------
                            # logger.debug(f"Parsed score: {score_text}, total: {total_score}")
                        except ValueError as e:
                            logger.error(f"Error converting score to int: {e}")
                            continue  # Пропускаем эту игру, если счет некорректный
                    else:
                        logger.debug(f"Score text '{score_text_raw}' doesn't match X:Y pattern")
                        continue  # Пропускаем, если формат не тот
                else:
                    logger.debug("game-score div not found near the label")
                    continue
            else:
                logger.debug("Label has no parent")
                continue

            # --- ИЩЕМ ВРЕМЯ ИГРЫ ---
            game_time = "N/A"
            # Ищем в родительском контейнере .simple-block
            parent_container = container.find_parent('div', class_='simple-block')
            time_found = False
            if parent_container:
                tags_div = parent_container.find('div', class_='tags')
                if tags_div:
                    time_elements = tags_div.find_all('div', class_='tag')
                    for time_element in time_elements:
                        time_text = time_element.get_text(strip=True)
                        # Проверяем, похоже ли это на дату/время
                        if re.match(r'\d{2}\.\d{2}\s*\d{2}:\d{2}', time_text):
                            # Форматируем время с пробелом
                            game_time = re.sub(r'(\d{2}\.\d{2})(\d{2}:\d{2})', r'\1 \2', time_text)
                            time_found = True
                            break

            # Если не нашли время в тегах, попробуем найти в тексте рядом
            if not time_found or game_time == "N/A":
                # Ищем дату в формате DD.MM HH:MM в тексте
                search_area = str(parent_container) if parent_container else str(container)
                date_match = re.search(r'(\d{2}\.\d{2}\s+\d{2}:\d{2})', search_area)
                if date_match:
                    game_time = date_match.group(1).strip()  # Убираем лишние пробелы
                    time_found = True

            # Еще одна попытка найти дату без пробела
            if not time_found or game_time == "N/A":
                search_area = str(parent_container) if parent_container else str(container)
                date_match = re.search(r'(\d{2}\.\d{2}\d{2}:\d{2})', search_area)
                if date_match:
                    raw_time = date_match.group(1)
                    # Вставляем пробел между датой и временем
                    formatted_time = f"{raw_time[:5]} {raw_time[5:]}"
                    game_time = formatted_time
                    time_found = True

            # --- ИЩЕМ ЛИГУ ---
            league = "Неизвестная лига"
            if parent_container:
                # Ищем div с классами tag me-2 text-truncate mw-100 d-inline-block
                # Это может быть ссылка на лигу или просто текст
                league_elements = parent_container.find_all('div',
                                                            class_='tag me-2 text-truncate mw-100 d-inline-block')
                for le in league_elements:
                    potential_league = le.get_text(strip=True)
                    if potential_league and len(potential_league) > 3 and potential_league != game_time:
                        league = potential_league
                        break
                # Альтернатива: ищем h3 перед блоком
                if league == "Неизвестная лига":
                    prev_h3 = parent_container.find_previous('h3')
                    if prev_h3:
                        potential_league = prev_h3.get_text(strip=True)
                        if potential_league and len(potential_league) > 3:
                            league = potential_league

            # --- ИЩЕМ ССЫЛКУ НА ИГРУ НА 1XBET ---
            game_link_1xbet = None
            if parent_container:
                # Ищем ссылку с классами tag text-decoration-none promo-1x d-inline-block
                # Основываясь на структуре из скриншота
                link_element = parent_container.find('a', class_='tag text-decoration-none promo-1x d-inline-block')
                if link_element:
                    game_link_1xbet = link_element.get('href')
                    # Если это относительная ссылка, делаем её абсолютной
                    if game_link_1xbet and game_link_1xbet.startswith('/'):
                        from urllib.parse import urljoin
                        game_link_1xbet = urljoin("https://tennis-score.pro", game_link_1xbet)

            game_data = {
                'time': game_time,
                'player1': player1,
                'player2': player2,
                'last_encounters_score': score_text,
                'total_last_encounters_score': total_score,
                'league': league,  # Добавляем лигу
                # --- Добавляем индивидуальные победы в данные игры ---
                'wins_player1': wins_player1,
                'wins_player2': wins_player2,
                # --- Добавляем ссылку на игру ---
                'game_link': game_link_1xbet,
                # --- Добавляем сам блок BeautifulSoup для повторного парсинга коэффициентов ---
                'soup_block': container  # <-- Передаем объект BeautifulSoup
                # ------------------------------------------------------------
            }

            games.append(game_data)
            logger.info(
                f"Found game: {player1} vs {player2}, score: {score_text} (sum: {total_score}), time: {game_time}, league: {league}")
            if game_link_1xbet:
                logger.info(f"  1xBet link: {game_link_1xbet}")

        except Exception as e:
            logger.error(f"Error parsing container: {e}", exc_info=True)
            continue

    # Удаляем дубликаты
    unique_games = []
    seen = set()
    for game in games:
        # В ключ включаем лигу, ссылку и счета для уникальности
        game_key = (game['player1'], game['player2'], game['last_encounters_score'], game.get('league', ''),
                    game.get('game_link', ''), game.get('wins_player1', 0), game.get('wins_player2', 0))
        if game_key not in seen:
            seen.add(game_key)
            unique_games.append(game)

    logger.info(f"Total unique games parsed: {len(unique_games)}")
    return unique_games
