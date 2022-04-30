import threading

import flask
import lxml.html
import lxml.etree
import requests
from bs4 import BeautifulSoup
import time
import datetime
import telebot
import cssselect
import os
from flask import Flask

# token = '1778090744:AAEaEx2yVHAakqGrV-Sn8q-STE_bIJzSbPM'
token = '743334117:AAHMwmjwVo0q-1HKQaHWPg0Td5dZ8ee6mDQ'

bot = telebot.TeleBot(token)
train_number = 0
last_date = -1
iteration = 0
sleep_time = 60

urls = [{"from": "Орша", "to": "Минск", "date": "2022-05-03"}]
queue = []
debug = False
server = flask.Flask(__name__)
search_thread = ""


def debug_print(string):
    print(f'{datetime.datetime.now()} - {string}')


@bot.message_handler(commands=['start'])
def start_message(message):
    # hideboard = telebot.types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, 'Выберите маршрут:')
    for number, url in enumerate(urls, start=1):
        bot.send_message(message.chat.id, f'{number}: {url["from"]} - {url["to"]} {url["date"]}')
        # bot.send_message(message.chat.id, 'Для выбора поезда используйте /set', reply_markup=keyboard)
        hello_message = '/setdate порядковый_номер - Для выбора маршрута\n\n'
        hello_message += '/add - Для добавления маршрута\n\n'
        hello_message += '/delete порядковый_номер - Для удаления маршрута'
        bot.send_message(message.chat.id, hello_message)
    debug_print(
        f'Start message sent! {message.chat.id, message.from_user.first_name, message.from_user.last_name, message.from_user.username}')


@bot.message_handler(commands=['setdate'])
def set_date(message):
    command = message.text.split()
    date_number = int(command[1]) - 1
    debug_print('Route selected!')
    bot.send_message(message.chat.id,
                     f'Список доступных поездов по маршруту {urls[date_number]["from"]} - {urls[date_number]["to"]} {urls[date_number]["date"]}:')
    debug_print(f'Collecting data for {urls[date_number]}')
    try:
        bot.send_message(message.chat.id, parser(urls[date_number])[1])
        # bot.send_message(message.chat.id, 'Для выбора поезда используйте /set', reply_markup=keyboard)
        hello_message = '/settrain порядковый_номер - Добавить поезд в лист ожидания\n\n'
        hello_message += '/update - Принудительно обновить\n\n'
        hello_message += '/time количество_секунд - Изменить время обновления\n\n'
        hello_message += '/debug - Включить/отключить режим отладки\n\n'
        hello_message += '/stop - Приостановить поиск'
        bot.send_message(message.chat.id, hello_message)
    except Exception as error:
        bot.send_message(message.chat.id, 'Во время получения данных произошла ошибка!')
        debug_print(error)
    debug_print('Train list sent!')


@bot.message_handler(commands=['stop'])
def stop_bot(message):
    global iteration
    iteration += 1
    bot.send_message(message.chat.id, 'Поиск приостановлен!')
    debug_print('Parsing stopped!')


@bot.message_handler(commands=['settrain'])
def set_train(message):
    global train_number
    command = message.text.split()
    train_number = int(command[1]) - 1
    queue.append({"url": urls[last_date], "number": train_number, "debug": 0})
    bot.send_message(message.chat.id, f'Поезд №{train_number + 1} выбран успешно!')
    debug_print(f'Train #{train_number + 1} added to queue!')
    global iteration
    iteration += 1
    global search_thread
    search_thread = threading.Thread(target=updater, args=(message, ))
    search_thread.start()
    # updater(message, iteration)


@bot.message_handler(commands=['seturl'])
def set_url(message):
    global url
    command = message.text.split()
    train_url = command[1]
    bot.send_message(message.chat.id, f'Адрес успешно установлен!')
    debug_print(f'New url set!')
    start_message()


@bot.message_handler(commands=['update'])
def fast_update(message):
    global iteration
    iteration += 1
    bot.send_message(message.chat.id, f'Ручное обновление выполнено успешно!')
    updater(message, iteration)


@bot.message_handler(commands=['time'])
def set_time(message):
    global sleep_time
    command = message.text.split()
    sleep_time = int(command[1]) - 3
    global iteration
    iteration += 1
    bot.send_message(message.chat.id, f'Установлено время обновления в {command[1]} секунд!')
    debug_print(f'Sleep time = {sleep_time}')
    updater(message, iteration)


@bot.message_handler(commands=['debug'])
def set_debug(message):
    global debug
    if not debug:
        debug = True
        bot.send_message(message.chat.id, f'Установлен режим отладки!')
        debug_print('Debug started')
    else:
        debug = False
        bot.send_message(message.chat.id, f'Режим отладки отключен!')
        debug_print('Debug stropped')
    global iteration
    iteration += 1
    updater(message, iteration)


@bot.message_handler(content_types=['text'])
def send_text(message):
    if message.text.lower() == 'привет':
        bot.send_message(message.chat.id, 'Привет, мой создатель')
    elif message.text.lower() == 'пока':
        bot.send_message(message.chat.id, 'Прощай, создатель')
    else:
        bot.send_message(message.chat.id, 'Команда не распознана')


def updater(message, start_iteration=0):
    # global iteration
    # while iteration == start_iteration:
    debug_print('Updating...')
    for number, train in enumerate(queue, start=1):
        temp = parser(train["url"], train["number"])
        result = str(temp[1]).replace('\n', ' ')
        debug_print(f"{number} - {result}")
        if temp[0] != -1 or debug is True:
            bot.send_message(message.chat.id, str(datetime.datetime.now()) + '\n' + str(temp[1]))
        else:
            debug_print('Telegram message was not sent!')
    debug_print('All trains updated!')
    time.sleep(sleep_time)


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
    return [status, ans]


def main():
    # Проверим, есть ли переменная окружения Heroku
    if "HEROKU" in list(os.environ.keys()):

        server = Flask(__name__)

        @server.route('/' + token, methods=['POST'])
        def get_message():
            # json_string = flask.request.stream.read().decode("utf-8")
            json_string = flask.request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return "!", 200

        @server.route('/', methods=["GET"])
        def index():
            bot.remove_webhook()
            bot.set_webhook(url=f'https://boiling-ridge-34241.herokuapp.com/{token}')
            return "Hello from Heroku!", 200

        server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
    else:
        # если переменной окружения HEROKU нету, значит это запуск с машины.
        # Удаляем вебхук на всякий случай, и запускаем с обычным поллингом.
        bot.remove_webhook()
        try:
            debug_print('Start pooling messages...')
            bot.polling(none_stop=True)
        except:
            debug_print('Polling stopped!')


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()
