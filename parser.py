import datetime
import os
import threading
import time
import flask
import lxml.etree
import cssselect
import lxml.html
import requests
import telebot
from flask import Flask
import config

TOKEN = config.token

bot = telebot.TeleBot(TOKEN)
# to set train after setting date
LAST_DATE = -1
SLEEP_TIME = 60
# routes url
URLS = [{"from": "Москва", "to": "Минск", "date": "2023-04-25"}]
# waiting list
QUEUE = []
# debug message mod
DEBUG = False
# for creating a new route
TEMP_DATA = {}
# for calculating max train number
TEMP_DATE_LENGTH = 0
# thread for searching process
SEARCH_THREAD = None
# event to stop thread
THREAD_STOP = False
server = flask.Flask(__name__)


def debug_print(string):
    print(f'{datetime.datetime.now()} - {string}')


@bot.message_handler(commands=['start'])
def start_message(message):
    # hideboard = telebot.types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, 'Выберите маршрут:')
    routes_list = ""
    for number, url in enumerate(URLS, start=1):
        routes_list += f'{number}: {url["from"]} - {url["to"]} {url["date"]}\n\n'
        # bot.send_message(message.chat.id, 'Для выбора поезда используйте /set', reply_markup=keyboard)
    bot.send_message(message.chat.id, routes_list)
    hello_message = '/setdate порядковый_номер - Для выбора маршрута\n\n'
    hello_message += '/adddate - Для добавления маршрута\n\n'
    hello_message += '/deletedate порядковый_номер - Для удаления маршрута\n\n'
    hello_message += '/list - Лист ожидания'
    bot.send_message(message.chat.id, hello_message)
    debug_print(f'Start message sent! {message.chat.id, message.from_user.first_name, message.from_user.last_name, message.from_user.username}')


@bot.message_handler(commands=['setdate'])
def set_date(message):
    command = message.text.split()
    try:
        date_number = int(command[1]) - 1
        if date_number < len(URLS):
            debug_print('Route selected!')
            bot.send_message(message.chat.id,
                             f'Список доступных поездов по маршруту {URLS[date_number]["from"]} - {URLS[date_number]["to"]} {URLS[date_number]["date"]}:')
            debug_print(f'Collecting data for {URLS[date_number]}')
            result = parser(URLS[date_number])
            global TEMP_DATE_LENGTH
            TEMP_DATE_LENGTH = result[1]
            bot.send_message(message.chat.id, result[2])
            # bot.send_message(message.chat.id, 'Для выбора поезда используйте /set', reply_markup=keyboard)
            hello_message = '/settrain порядковый_номер - Добавить поезд в лист ожидания\n\n'
            hello_message += '/update - Принудительно обновить\n\n'
            hello_message += '/time количество_секунд - Изменить время обновления\n\n'
            hello_message += '/debug - Включить/отключить режим отладки\n\n'
            hello_message += '/stop - Приостановить поиск'
            bot.send_message(message.chat.id, hello_message)
            debug_print('Train list sent!')
        else:
            bot.send_message(message.chat.id, 'Маршрута с таким номером не существует')
    except Exception as error:
        bot.send_message(message.chat.id, 'Во время получения данных произошла ошибка!')
        debug_print(error)


@bot.message_handler(commands=['adddate'])
def add_date(message):
    msg = bot.send_message(message.chat.id, 'Введите станцию отправления:')
    global TEMP_DATA
    TEMP_DATA = {}
    bot.register_next_step_handler(msg, step_1)


def step_1(message):
    global TEMP_DATA
    TEMP_DATA["from"] = message.text
    msg = bot.send_message(message.chat.id, 'Введите станцию назначения:')
    bot.register_next_step_handler(msg, step_2)


def step_2(message):
    global TEMP_DATA
    TEMP_DATA["to"] = message.text
    msg = bot.send_message(message.chat.id, 'Введите дату в формате YYYY-MM-DD:')
    bot.register_next_step_handler(msg, submit_step)


def submit_step(message):
    global TEMP_DATA
    TEMP_DATA["date"] = message.text
    URLS.append(TEMP_DATA)
    bot.send_message(message.chat.id, 'Маршрут успешно добавлен!')
    debug_print(f'Route added! ({TEMP_DATA})')


@bot.message_handler(commands=['deletedate'])
def delete_date(message):
    command = message.text.split()
    try:
        date_number = int(command[1]) - 1
        if len(URLS) > date_number >= 0:
            URLS.pop(date_number)
            bot.send_message(message.chat.id, 'Маршрут успешно удален!')
            debug_print(f'Route deleted! ({TEMP_DATA})')
        else:
            bot.send_message(message.chat.id, 'Маршрута с таким номером не существует')
    except Exception as error:
        bot.send_message(message.chat.id, 'Во время получения данных произошла ошибка!')
        debug_print(error)


@bot.message_handler(commands=['stop'])
def stop_bot(message):
    global THREAD_STOP
    THREAD_STOP = True
    bot.send_message(message.chat.id, 'Поиск приостановлен!')
    debug_print('Parsing stopped!')


@bot.message_handler(commands=['list'])
def start_message(message):
    if QUEUE:
        ans = "Лист ожидания:\n\n"
        for number, train in enumerate(QUEUE, start=1):
            ans += f'{number}: {train["url"]["from"]} - {train["url"]["to"]} {train["url"]["date"]}, поезд №{train["number"] + 1}\n\n'
        ans += '/deletetrain порядковый_номер - Удалить поезд из листа ожидания\n\n'
        bot.send_message(message.chat.id, ans)

        debug_print(f'Queue: {QUEUE}')
    else:
        bot.send_message(message.chat.id, 'Лист ожидания пуст!')


@bot.message_handler(commands=['settrain'])
def set_train(message):
    command = message.text.split()
    try:
        train_number = int(command[1]) - 1
        global TEMP_DATE_LENGTH
        if TEMP_DATE_LENGTH > train_number >= 0:
            QUEUE.append({"url": URLS[LAST_DATE], "number": train_number, "debug": 0})
            bot.send_message(message.chat.id, f'Поезд №{train_number + 1} выбран успешно!')
            debug_print(f'Train #{train_number + 1} added to queue!')
            global SEARCH_THREAD
            SEARCH_THREAD = threading.Thread(target=updater, args=(message,))
            SEARCH_THREAD.start()
        else:
            bot.send_message(message.chat.id, 'Поезда с таким номером не существует')
    except Exception as error:
        bot.send_message(message.chat.id, 'Во время получения данных произошла ошибка!')
        debug_print(error)


@bot.message_handler(commands=['deletetrain'])
def delete_train(message):
    command = message.text.split()
    try:
        train_number = int(command[1]) - 1
        if len(QUEUE) > train_number >= 0:
            debug_print(f'Train deleted! ({QUEUE[train_number]})')
            QUEUE.pop(train_number)
            bot.send_message(message.chat.id, 'Поезд успешно удален из списка ожидания!')
        else:
            bot.send_message(message.chat.id, 'Поезда с таким номером в списке ожидания не существует')
    except Exception as error:
        bot.send_message(message.chat.id, 'Во время получения данных произошла ошибка!')
        debug_print(error)


@bot.message_handler(commands=['update'])
def fast_update(message):
    # TODO fix
    SEARCH_THREAD.start()
    bot.send_message(message.chat.id, 'Ручное обновление выполнено успешно!')


@bot.message_handler(commands=['time'])
def set_time(message):
    global SLEEP_TIME
    command = message.text.split()
    try:
        new_time = int(command[1]) - 3
        if new_time > 0:
            SLEEP_TIME = new_time
            bot.send_message(message.chat.id, f'Установлено время обновления в {command[1]} секунд!')
            debug_print(f'Sleep time = {SLEEP_TIME}')
        else:
            bot.send_message(message.chat.id, f'Укажите время более трех секунд!')
    except Exception as error:
        bot.send_message(message.chat.id, 'Во время получения данных произошла ошибка!')
        debug_print(error)


@bot.message_handler(commands=['debug'])
def set_debug(message):
    global DEBUG
    if not DEBUG:
        DEBUG = True
        bot.send_message(message.chat.id, 'Установлен режим отладки!')
        debug_print('Debug started')
    else:
        DEBUG = False
        bot.send_message(message.chat.id, 'Режим отладки отключен!')
        debug_print('Debug stropped')


@bot.message_handler(content_types=['text'])
def send_text(message):
    if message.text.lower() == 'привет':
        bot.send_message(message.chat.id, 'Привет, создатель')
    elif message.text.lower() == 'пока':
        bot.send_message(message.chat.id, 'Прощай, создатель')
    else:
        bot.send_message(message.chat.id, 'Команда не распознана')


def updater(message):
    debug_print('Thread started!')
    while True:
        global QUEUE
        global THREAD_STOP
        if THREAD_STOP or not QUEUE:
            THREAD_STOP = False
            debug_print('Thread stopped!')
            break
        debug_print('Updating...')
        debug_print(f'{QUEUE}')
        for number, train in enumerate(QUEUE, start=1):
            temp = parser(train["url"], train["number"])
            result = str(temp[2]).replace('\n', ' ')
            debug_print(f"{number} - {result}")
            if temp[0] != -1 or DEBUG is True:
                bot.send_message(message.chat.id, str(datetime.datetime.now()) + '\n' + str(temp[2]))
            else:
                debug_print('Telegram message was not sent!')
        debug_print('All trains updated!')
        time.sleep(SLEEP_TIME)


def parser(current_url, current_train=-1):
    # page - full code
    url = f'https://pass.rw.by/ru/route/?from={current_url["from"]}&to={current_url["to"]}&date={current_url["date"]}'
    page = requests.get(url)
    debug_print(f'{page}')
    # make a lxml tree
    tree = lxml.html.fromstring(page.content)
    # print(lxml.html.tostring(tree))
    # search for trains by ccs
    transport_res = tree.cssselect('div.sch-table__row-wrap')
    if current_train != -1:
        transport_res = transport_res[current_train]
    result = []
    status = -1
    ans = ''
    # for each train
    for number, data in enumerate(transport_res, start=1):
        # strip - without spaces
        train_name = data.cssselect('span.train-route')[0].text_content().strip()
        train_departure = data.cssselect('div.train-from-time')[0].text_content().strip()
        train_arrive = data.cssselect('div.train-to-time')[0].text_content().strip()
        train_duration = data.cssselect('div.train-duration-time')[0].text_content().strip()
        train_tickets = data.cssselect('div.sch-table__tickets')[0].text_content().strip()

        # print for debug
        if current_train == -1:
            ans += f'{number}: {train_name} {train_departure} {train_arrive} {train_duration}\n'
        else:
            ans += f'{train_name} {train_departure} {train_arrive} {train_duration}\n'
        ans += 'Билеты:\n'

        # collecting info about only tickets for qt
        tickets = ''
        if train_tickets != '\n':
            # items is []
            ticket_items = data.cssselect('div.sch-table__t-item')
            for item in ticket_items:
                status = 0
                # each item includes name, free, [] of prices
                ticket_type = item.cssselect('div.sch-table__t-name')
                ticket_free = item.cssselect('a.sch-table__t-quant')
                ticket_prices = item.cssselect('span.ticket-cost')

                if ticket_type[0].text is not None and ticket_type[0].text != ' ':
                    ans += f'Тип: {ticket_type[0].text}'
                    tickets += f'Тип: {ticket_type[0].text}'
                else:
                    ans += 'Tип: --------'
                    tickets += 'Tип: --------'

                if ticket_free[0].text_content() is not None:
                    ans += f' --- Свободно: {ticket_free[0].text_content()}'
                    tickets += f' --- Свободно: {ticket_free[0].text_content()}'
                else:
                    ans += ' --- Свободно: ---'
                    tickets += ' --- Свободно: ---'

                if ticket_prices is not None:
                    # if it is not one price
                    for num, price in enumerate(ticket_prices):
                        if num < 1:
                            ans += f' --- Цена: {price.text}\n'
                            tickets += f' --- Цена: {price.text}\n'
                        else:
                            ans += f'-------------------------------------- Цена: {price.text}\n'
                            tickets += f'-------------------------------------- Цена: {price.text}\n'
                else:
                    ans += ' --- Цена: ---\n'
                    tickets += ' --- Цена: ---\n'

        train_tickets_bad = data.cssselect('div.sch-table__no-info')
        if train_tickets_bad:
            train_tickets_bad = data.cssselect('div.sch-table__no-info')
            ans += f'{train_tickets_bad[0].text.strip()}\n'
            tickets = f'{train_tickets_bad[0].text.strip()}\n'
        ans += '\n'

        tickets = tickets[:-1]  # убрать лишний перевод строки
        str_count = tickets.count("\n")  # количество строк

        # полная информация о поезде
        # train_info = [number, train_name, train_departure, train_arrive, train_duration, str_count, tickets]
        train_info = {'number': number, 'train_name': train_name, 'train_departure': train_departure,
                      'train_arrive': train_arrive, 'train_duration': train_duration,
                      'str_count': str_count, 'tickets': tickets}
        result.append(train_info)
    ans = ans[:-1]
    # print(status)
    # print(ans)
    return [status, len(transport_res), ans]


def main():
    # Проверим, есть ли переменная окружения Heroku
    if "HEROKU" in list(os.environ.keys()):

        server = Flask(__name__)

        @server.route('/' + TOKEN, methods=['POST'])
        def get_message():
            # json_string = flask.request.stream.read().decode("utf-8")
            json_string = flask.request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return "!", 200

        @server.route('/', methods=["GET"])
        def index():
            bot.remove_webhook()
            bot.set_webhook(url=f'https://boiling-ridge-34241.herokuapp.com/{TOKEN}')
            return "Hello from Heroku!", 200

        server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
    else:
        # если переменной окружения HEROKU нету, значит это запуск с машины.
        # Удаляем вебхук на всякий случай, и запускаем с обычным поллингом.
        try:
            bot.remove_webhook()
        except Exception as error:
            debug_print(f'Webhook removing bad! Error: {error}')
        while True:
            try:
                debug_print('Start pooling messages...')
                bot.polling(none_stop=True)
            except Exception as error:
                debug_print(f'Polling stopped! Error: {error}')
            else:
                bot.stop_polling()
                debug_print("Polling finished!")
                break


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()
