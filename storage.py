import json
import logging

from constants import STATE_FILE

_EMPTY_STATE = {'last_id': None, 'last_page': None}


def load_state():
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        return dict(_EMPTY_STATE)
    except (json.JSONDecodeError, OSError):
        logging.warning('state.json invalido, se reinicia estado')
        return dict(_EMPTY_STATE)
    return {'last_id': data.get('last_id'), 'last_page': data.get('last_page')}


def save_state(last_id, last_page):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump({'last_id': last_id, 'last_page': last_page}, f)
