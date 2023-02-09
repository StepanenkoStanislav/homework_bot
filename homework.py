import os
import time
from functools import wraps
from datetime import datetime

import telegram
import requests
import logging
from dotenv import load_dotenv

from exceptions import (VarEnvError, ResponseKeyError, EmptyHomeworksListError,
                        HomeworkStatusError, HomeworkVerdictError,
                        ApiNotAvailable, TelegramSendMessageError,
                        HomeworkNameError)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_DATE = {'year': 2023, 'month': 1, 'day': 1}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
log_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - line %(lineno)s - %(message)s')
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(log_formatter)
logger.addHandler(stream_handler)


def previous_homework_status_decorator(func):
    """Сравниваем статус, с предыдущим.
    В случае обновления статуса, возвращаем сообщение.
    """
    previous_status = ''

    @wraps(func)
    def wrapper(homework):
        nonlocal previous_status
        data = func(homework)
        if data['status'] != previous_status:
            previous_status = data['status']
            return data['message']
        logger.debug(
            f'Статус домашней работы не изменился: "{data["status"]}"')
    return wrapper


def check_tokens() -> None:
    """Проверяем наличие необходимых переменных окружения."""
    for env_var in [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]:
        if env_var is None:
            logger.critical(f'Отсутствует обязательная переменная '
                            f'окружения "{env_var}"')
            raise VarEnvError(f'Отсутствует обязательная переменная '
                              f'окружения "{env_var}"')


def send_message(bot: telegram.Bot, message):
    """Отправляем сообщение об обновлённом статусе пользователю."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Бот отправил сообщение "{message}"')
    except Exception as error:
        logger.error(f'Ошибка при отправке сообщения в telegram {error}')
        raise TelegramSendMessageError(error)


def get_api_answer(timestamp):
    """Делаем запрос к API, возвращаем преобразованный к словарю результат."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != 200:
            logger.error(f'Api по адресу {ENDPOINT} не отвечает')
            raise ApiNotAvailable(f'Api по адресу {ENDPOINT} не отвечает')
        return response.json()
    except requests.RequestException as error:
        logger.error(f'Ошибка при подключении к API по '
                     f'адресу {ENDPOINT}\n{error}')
        raise Exception(f'Ошибка при подключении к API по адресу {ENDPOINT}')


def check_response(response):
    """Проверяем ответ API на наличие необходимых ключей и домашних работ."""
    if type(response) != dict:
        logger.error(f'Ответ API {response} не является словарем')
        raise TypeError(f'Ответ API {response} не является словарем')
    for key in ['homeworks', 'current_date']:
        if response.get(key) is None:
            logger.error(f'В ответе API нет ключа {key}\n'
                         f'Ключи ответа: {list(response.keys())}')
            raise ResponseKeyError(f'В ответе API нет ключа {key}\n'
                                   f'Ключи ответа: {list(response.keys())}')
    if type(response['homeworks']) != list:
        logger.error('Домашние задания в ответе API не является списком')
        raise TypeError('Домашние задания в ответе API не является списком')
    if len(response['homeworks']) == 0:
        logger.error(f'Нет домаших работ за выбранный период {HOMEWORK_DATE}')
        raise EmptyHomeworksListError(f'Нет домаших работ за выбранный период '
                                      f'{HOMEWORK_DATE}')


@previous_homework_status_decorator
def parse_status(homework):
    """Получаем статус последней домашней работы.
    Возвращаем статус и сообщение, которое будет отправлено в случае,
    если статус изменился.
    """
    homework_status = homework.get('status')
    if homework_status is None:
        logger.error(f'В homework отсутствует "status"\n'
                     f'Ключи: {list(homework.keys())}')
        raise HomeworkStatusError(f'В homework отсутствует "status"\n'
                                  f'Ключи: {list(homework.keys())}')

    homework_verdict = HOMEWORK_VERDICTS.get(homework_status)
    if homework_verdict is None:
        logger.error(f'Статус "{homework_status}" отсутствует\n'
                     f'Возможные статусы: {list(HOMEWORK_VERDICTS.keys())}')
        raise HomeworkVerdictError(f'Статус "{homework_status}" отсутствует'
                                   f'\n Возможные статусы: '
                                   f'{list(HOMEWORK_VERDICTS.keys())}')

    homework_name = homework.get('homework_name')
    if homework_name is None:
        logger.error('В ответе API отсутствует ключ "homework_name"')
        raise HomeworkNameError(
            'В ответе API отсутствует ключ "homework_name"')
    return {
        'status': homework_status,
        'message': (f'Изменился статус проверки работы "'
                    f'{homework_name}". {homework_verdict}')
    }


def main():
    """Основная логика работы бота."""
    exception_telegram_message = ''
    while True:
        try:
            date = datetime(*HOMEWORK_DATE.values())
            timestamp = int(datetime.timestamp(date))
            check_tokens()
            bot = telegram.Bot(token=TELEGRAM_TOKEN)
            response = get_api_answer(timestamp)
            check_response(response)
            message = parse_status(response['homeworks'][0])
            if message:
                send_message(bot, message)
            time.sleep(RETRY_PERIOD)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if type(error).__name__ == 'VarEnvError':
                break
            if (type(error).__name__ != 'TelegramSendMessageError'
                    and message != exception_telegram_message):
                exception_telegram_message = message
                bot = telegram.Bot(token=TELEGRAM_TOKEN)
                send_message(bot, message)
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
