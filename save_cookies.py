
import json
import sys

COOKIES_FILE = 'cookies.json'

def save_cookies_from_json_string(json_cookie_string):
    try:
        cookies_dict = json.loads(json_cookie_string)
        with open(COOKIES_FILE, 'w') as f:
            json.dump(cookies_dict, f)
        print('Cookies saved from browser session.')
    except json.JSONDecodeError:
        print('Error: Invalid JSON string provided.')

if __name__ == '__main__':
    if len(sys.argv) > 1:
        save_cookies_from_json_string(sys.argv[1])
    else:
        print("Usage: python save_cookies.py \"json_cookie_string\"")


