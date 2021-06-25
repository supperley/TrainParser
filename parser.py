import flask
import requests
from bs4 import BeautifulSoup
import time
import datetime
import telebot
import os
from flask import Flask

token = '1778090744:AAEaEx2yVHAakqGrV-Sn8q-STE_bIJzSbPM'
# token = '743334117:AAHMwmjwVo0q-1HKQaHWPg0Td5dZ8ee6mDQ'

bot = telebot.TeleBot(token)
train_number = 0
iteration = 0
sleep_time = 57
url = 'https://pass.rw.by/ru/route/?from=%D0%9E%D1%80%D1%88%D0%B0&from_exp=2100170&from_esr=166403&to=%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B0&to_exp=2000000&to_esr=0&front_date=15+%D0%B8%D1%8E%D0%BB%D1%8F.+2021&date=2021-07-15'
debug = False
server = flask.Flask(__name__)


@bot.message_handler(commands=['start'])
def start_message(message):
    hideboard = telebot.types.ReplyKeyboardRemove()
    # keyboard = telebot.types.InlineKeyboardMarkup()
    # keyboard = telebot.types.ReplyKeyboardMarkup()
    # keyboard.row(telebot.types.InlineKeyboardButton('Set', callback_data='/set'),
    #              telebot.types.InlineKeyboardButton('Update', callback_data='/update'),
    #              telebot.types.InlineKeyboardButton('Restart', callback_data='/start'))
    # keyboard.row(telebot.types.KeyboardButton('/set'),
    #              telebot.types.KeyboardButton('/update'),
    #              telebot.types.KeyboardButton('/start'))
    bot.send_message(message.chat.id, 'Привет, вот список доступных поездов:')
    bot.send_message(message.chat.id, parser_2())
    # bot.send_message(message.chat.id, 'Для выбора поезда используйте /set', reply_markup=keyboard)
    hello_message = 'Для выбора поезда используйте /set "число"\n\n'
    hello_message += 'Для ручного обновления используйте /update\n\n'
    hello_message += 'Для изменения времени обновления используйте /time "число"\n\n'
    hello_message += 'Для включения/выключения режима отладки используйте /debug\n\n'
    hello_message += 'Для завершения работы используйте /stop'
    bot.send_message(message.chat.id, hello_message, reply_markup=hideboard)
    print('Start message sent!')


@bot.message_handler(commands=['stop'])
def stop_bot(message):
    global iteration
    iteration += 1
    bot.send_message(message.chat.id, 'Поиск приостановлен!')
    print('Parsing stopped!')


@bot.message_handler(commands=['set'])
def set_train(message):
    global train_number
    command = message.text.split()
    train_number = int(command[1]) - 1
    bot.send_message(message.chat.id, f'Поезд №{train_number + 1} выбран успешно!')
    print(f'Train #{train_number + 1} set!')
    global iteration
    iteration += 1
    updater(message, iteration)


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
    print(f'Sleep time = {sleep_time}')
    updater(message, iteration)


@bot.message_handler(commands=['debug'])
def set_debug(message):
    global debug
    if not debug:
        debug = True
        bot.send_message(message.chat.id, f'Установлен режим отладки!')
        print('Debug started')
    else:
        debug = False
        bot.send_message(message.chat.id, f'Режим отладки отключен!')
        print('Debug stropped')
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


def updater(message, start_iteration):
    global iteration
    while iteration == start_iteration:
        current_datetime = datetime.datetime.now()
        print(current_datetime)
        temp = parser_3(train_number)
        print(temp[1])
        if temp[0] is not None or debug is True:
            bot.send_message(message.chat.id, str(current_datetime) + '\n' + str(temp[1]))
        else:
            print('Telegram message was not sent!')
        time.sleep(sleep_time)


def parser_2():
    global url
    response = ''
    try:
        response = requests.get(url)
    except ConnectionResetError:
        print("Connection error!")
    soup = BeautifulSoup(response.text, 'lxml')
    # print(soup)
    items = soup.find_all('div', class_='sch-table__row-wrap')
    # print(items)
    ans = ''

    for number, data in enumerate(items, start=1):
        train_name = data.find('span', class_='train-route').text.strip()
        train_departure = data.find('div', class_='sch-table__time train-from-time').text.strip()
        train_arrive = data.find('div', class_='sch-table__time train-to-time').text.strip()
        train_duration = data.find('div', class_='sch-table__duration train-duration-time').text.strip()
        train_tickets = data.find('div', class_='sch-table__tickets')

        ans += f'{number}: {train_name} {train_departure} {train_arrive} {train_duration}\n'
        ans += 'Билеты:\n'

        if train_tickets != '\n':
            ticket_types = data.find_all('div', class_='sch-table__t-name')
            ticket_space = data.find_all('a', class_='sch-table__t-quant js-train-modal dash')
            ticket_cost = data.find_all('span', class_='ticket-cost')
            for j in range(len(ticket_types)):
                # if ticket_types[j]:
                #     print(f'Тип: {ticket_types[j].text}')
                # if ticket_space[j]:
                #     print(f'Свободно: {ticket_space[j].text}')
                # if ticket_cost[j]:
                #     print(f'Цена: {ticket_cost[j].text}')
                ans += f'Тип: {ticket_types[j].text} --- Свободно: {ticket_space[j].text} --- Цена: {ticket_cost[j].text}\n'

        train_tickets_bad = data.find('div', class_='sch-table__no-info')
        if train_tickets_bad:
            train_tickets_bad = data.find('div', class_='sch-table__no-info').text.strip()
            ans += f'{train_tickets_bad}\n'
        ans += '\n'

    return ans


def parser_3(number):
    global url
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'lxml')
    items = soup.find_all('div', class_='sch-table__row-wrap')

    train_name = items[number].find('span', class_='train-route').text.strip()
    train_departure = items[number].find('div', class_='sch-table__time train-from-time').text.strip()
    train_arrive = items[number].find('div', class_='sch-table__time train-to-time').text.strip()
    train_duration = items[number].find('div', class_='sch-table__duration train-duration-time').text.strip()
    train_tickets = items[number].find('div', class_='sch-table__tickets')
    ans = f'{train_name} {train_departure} {train_arrive} {train_duration}'
    ans += '\nБилеты:\n'
    if train_tickets:
        ticket_types = items[number].find_all('div', class_='sch-table__t-name')
        ticket_space = items[number].find_all('a', class_='sch-table__t-quant js-train-modal dash')
        ticket_cost = items[number].find_all('span', class_='ticket-cost')
        for j in range(len(ticket_types)):
            ans += f'Тип: {ticket_types[j].text} Свободно: {ticket_space[j].text} Цена: {ticket_cost[j].text}\n'

    train_tickets_bad = items[number].find('div', class_='sch-table__no-info')
    if train_tickets_bad:
        train_tickets_bad = items[number].find('div', class_='sch-table__no-info').text.strip()
        ans += f'{train_tickets_bad}'

    code = 0
    if train_tickets.text == '\n':
        code = None

    return [code, ans]


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
        bot.polling(none_stop=True)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()
