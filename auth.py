import requests
import os
import json
from bs4 import BeautifulSoup

LOGIN_URL = 'https://tennis-score.pro/login/'
UP_GAMES_URL = 'https://tennis-score.pro/up-games/'
EMAIL = 'логин тенис скор'
PASSWORD = 'пароль'
COOKIES_FILE = 'cookies.json'

def login_and_save_cookies():
    session = requests.Session()
    
    # Add headers to mimic a real browser
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    
    # Try to load cookies
    if os.path.exists(COOKIES_FILE):
        with open(COOKIES_FILE, 'r') as f:
            try:
                loaded_cookies = json.load(f)
                # Convert the dictionary back to a CookieJar object
                session.cookies.update(requests.utils.cookiejar_from_dict(loaded_cookies))
                print('Cookies loaded.')
                # Verify if cookies are still valid by trying to access a protected page
                response = session.get(UP_GAMES_URL)
                print(f"Response status code after loading cookies: {response.status_code}")
                print(f"Response URL after loading cookies: {response.url}")
                if response.status_code == 200 and 'Авторизация' not in response.text: # Check if redirected to login page
                    print('Cookies are valid.')
                    return session
                else:
                    print('Cookies expired or invalid. Logging in again.')
            except json.JSONDecodeError:
                print('Error decoding cookies.json. Logging in again.')

    # If no cookies or invalid, perform login
    # First, get the login page to retrieve any CSRF tokens or hidden fields
    response = session.get(LOGIN_URL)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract all hidden input fields from the login form
    hidden_inputs = {}
    login_form = soup.find('form', {'name': 'form_auth'})
    if login_form:
        for input_tag in login_form.find_all('input', type='hidden'):
            hidden_inputs[input_tag.get('name')] = input_tag.get('value')

    payload = {
        'USER_LOGIN': EMAIL,
        'USER_PASSWORD': PASSWORD,
        **hidden_inputs # Add all hidden inputs to the payload
    }
    
    # The action URL for the form is '/login/?login=yes'
    login_action_url = LOGIN_URL + '?login=yes'
    response = session.post(login_action_url, data=payload)

    if response.status_code == 200 and 'Выйти' in response.text: # Check for successful login indicator
        print('Login successful.')
        with open(COOKIES_FILE, 'w') as f:
            json.dump(requests.utils.dict_from_cookiejar(session.cookies), f)
        print('Cookies saved.')
        return session
    else:
        print('Login failed.')
        print(response.text)
        return None

if __name__ == '__main__':
    session = login_and_save_cookies()
    if session:
        print('Session created successfully.')
        # You can now use this session to make requests to protected pages
        # For example:
        # response = session.get(UP_GAMES_URL)
        # print(response.text)
    else:
        print('Failed to create session.')

