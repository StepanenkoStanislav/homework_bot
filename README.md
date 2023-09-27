# Проект Telegram Bot для обновлений статуса проверки домашней работы

## Описание проекта
 В этом проекте реализован Telegram Bot для обновлений статуса проверки домашней работы на Яндекс Практикум.
 Функции бота:
- раз в 10 минут опрашивает API сервис Практикум.Домашка и проверяет статус отправленной на ревью домашней работы;
- при обновлении статуса анализирует ответ API и отправляет соответствующее уведомление в Telegram;
- логирует свою работу и сообщает о важных проблемах сообщением в Telegram.


## Установка

Клонировать репозиторий и перейти в него в командной строке:

```
git clone 
```

```
cd homework_bot
```

Cоздать и активировать виртуальное окружение:

```
python3 -m venv venv
```

* Если у вас Linux/macOS

    ```
    source venv/bin/activate
    ```

* Если у вас windows

    ```
    source venv/scripts/activate
    ```

Установить зависимости из файла requirements.txt:

```
python3 -m pip install --upgrade pip
```

```
pip install -r requirements.txt
```

В директории _homework_bot_ необходимо создать файл _.env_, где необходимо указать:
```
PRACTICUM_TOKEN=PRACTICUM_TOKEN - токен для доступа к API Практикум.Домашка

TELEGRAM_TOKEN=TELEGRAM_TOKEN - Telegram токен

TELEGRAM_CHAT_ID=1234 - Id чата Telegram
```



### Запуск проекта
```python
# В директории telegram_bot
python3 homework.py
```


## Технологии

<div>
  <img src="https://github.com/devicons/devicon/blob/master/icons/python/python-original.svg" title="python" alt="python" width="40" height="40"/>&nbsp
  <img src="https://upload.wikimedia.org/wikipedia/commons/8/82/Telegram_logo.svg" title="telegram" alt="telegram" width="36" height="36"/>&nbsp
</div>

В проекте используются следующие технологии:

- Python 3.7

- python-telegram-bot 13.7
