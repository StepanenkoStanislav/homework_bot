import http
import os
import time
import sys

import telegram
import requests
import logging
from dotenv import load_dotenv

from exceptions import DontSendTelegramError, SendTelegramError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 60 * 10
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    format=('%(asctime)s - %(name)s - %(levelname)s - '
            'line %(lineno)s - %(message)s'),
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(filename='logger.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


def check_tokens() -> bool:
    """Проверяем наличие необходимых переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot: telegram.Bot, message: str) -> None:
    """Отправляем сообщение об обновлённом статусе пользователю."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.error.TelegramError:
        logger.error(f'Ошибка при отправке в telegram сообщения "{message}"')
    else:
        logger.debug(f'Бот отправил сообщение "{message}"')


def get_api_answer(timestamp: int) -> dict:
    """Делаем запрос к API, возвращаем преобразованный к словарю результат."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != http.HTTPStatus.OK:
            raise DontSendTelegramError(
                f'Api по адресу {ENDPOINT} не отвечает headers: {HEADERS}, '
                f'params: {payload}, status_code: {response.status_code} '
                f'{response.reason}, text: {response.text}')
        return response.json()
    except requests.RequestException as error:
        raise SendTelegramError('Ошибка при подключении к API по адресу '
                                f'{ENDPOINT}, headers: {HEADERS}, '
                                f'params: {payload}, {error}')


def check_response(response: dict) -> None:
    """Проверяем ответ API на наличие необходимых ключей и домашних работ."""
    if not isinstance(response, dict):
        raise TypeError(f'Ответ API {response} не является словарем')
    if response.get('homeworks') is None:
        raise DontSendTelegramError('В ответе API нет ключа "homeworks", '
                                    f'ключи ответа: {list(response.keys())}')
    if response.get('current_date') is None:
        raise DontSendTelegramError('В ответе API нет ключа "current_date", '
                                    f'ключи ответа: {list(response.keys())}')
    if not isinstance(response['homeworks'], list):
        raise TypeError('Домашние задания в ответе API не является списком')


def parse_status(homework: dict) -> str:
    """Получаем статус последней домашней работы.
    Возвращаем статус и сообщение, которое будет отправлено в случае,
    если статус изменился.
    """
    homework_status = homework.get('status')
    if homework_status is None:
        raise DontSendTelegramError('В homework отсутствует "status"'
                                    f'Ключи: {list(homework.keys())}')

    homework_verdict = HOMEWORK_VERDICTS.get(homework_status)
    if homework_verdict is None:
        raise DontSendTelegramError(f'Статус "{homework_status}" отсутствует'
                                    'Возможные статусы: '
                                    f'{list(HOMEWORK_VERDICTS.keys())}')

    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise DontSendTelegramError(
            'В ответе API отсутствует ключ "homework_name"')
    return (f'Изменился статус проверки работы "{homework_name}". '
            f'{homework_verdict}')


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        error_message = 'Отсутствует обязательная переменная окружения'
        logger.critical(error_message)
        sys.exit(error_message)

    previous_message = ''
    exception_previous_message = ''
    timestamp = int(time.time())
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            timestamp = response.get('current_date', int(time.time()))
            homeworks = response['homeworks']
            if homeworks:
                message = parse_status(homeworks[0])
                if message != previous_message:
                    send_message(bot, message)
                    previous_message = message
                else:
                    logger.debug('Статус домашней работы не изменился')
            else:
                logger.debug('response["homeworks"] содержит пустой список')
        except DontSendTelegramError as error:
            logger.error(f'Сбой в работе программы: {error}', exc_info=True)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message, exc_info=True)
            if message != exception_previous_message:
                exception_previous_message = message
                send_message(bot, exception_previous_message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
