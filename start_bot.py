import random

from sqlalchemy import func, or_, and_
from tg_bot_db import Session, Translate, TargetWord, User
from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup

state_storage = StateMemoryStorage()
token_bot = ''
bot = TeleBot(token_bot, state_storage=state_storage)

known_users = []
userStep = {}
buttons = []


def all_users():
    """Функция возвращает список с кортежами айдишников всех пользователей"""
    session = Session()
    kn_users = session.query(User.tg_id).all()
    session.close()
    return kn_users


def add_user(id):
    """Функция принимает id пользователя и добавляет его в БД"""
    session = Session()
    if (id,) not in all_users():
        id = User(tg_id=id)
        session.add(id)
        session.commit()
    session.close()


def choose_wrong_words():
    """Функция генерирует и возвращает список из 3 неправильных переводов"""
    session = Session()
    words = list(word[0] for word in
                 session.query(TargetWord.word).filter(TargetWord.id != word_id[0]).order_by(
                     func.random()).limit(3).all())
    session.close()
    return words


def choose_target_word(user_id):
    """Функция принимает id пользователи и рандомно выбирает для него слово"""
    session = Session()
    choose_word = ''.join(*(session.query(TargetWord.word).join(TargetWord.user).
                            filter(or_(TargetWord.user_tg_id == 0, TargetWord.user_tg_id == user_id)).
                            order_by(func.random()).first()))
    global word_id
    word_id = session.query(Translate.id).join(Translate.target_word).filter(TargetWord.word == choose_word)[0]
    session.close()
    return choose_word


def translate_word():
    """Функция возвращает перевод слова в зависимости от target_word_id"""
    session = Session()
    translate = ''.join(*(session.query(Translate.translate).
                          join(Translate.target_word).filter(Translate.target_word_id == word_id[0]).first()))
    session.close()
    return translate


def show_hint(*lines):
    """Функция возвращает текст подсказки, в зависимости от того, правильно ли юзер угадал перевод"""
    return '\n'.join(lines)


def show_target(data):
    """Функция возвращает слово и его перевод"""
    return f"{data['target_word']} -> {data['translate_word']}"


class Command:
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово🔙'
    NEXT = 'Дальше ⏭'


class MyStates(StatesGroup):
    target_word = State()
    translate_word = State()
    another_words = State()


def get_user_step(uid):
    if uid in userStep:
        return userStep[uid]
    else:
        known_users.append(uid)
        userStep[uid] = 0
        print("New user detected, who hasn't used \"/start\" yet")
        return 0


@bot.message_handler(commands=['cards', 'start'])
def create_cards(message):
    """Функция выбирает слово и показывает его юзеру"""
    user_id = message.from_user.id
    cid = message.chat.id
    if (user_id,) not in all_users():
        add_user(user_id)
        known_users.append(cid)
        userStep[cid] = 0
        bot.send_message(cid, """Привет 👋 Давай попрактикуемся в английском языке. 
Тренировки можешь проходить в удобном для себя темпе.

У тебя есть возможность использовать тренажёр, как конструктор, и собирать свою собственную базу для обучения. 
Для этого воспрользуйся инструментами:

добавить слово ➕,
удалить слово 🔙.
Ну что, начнём ⬇️'""")
    markup = types.ReplyKeyboardMarkup(row_width=2)

    global buttons
    buttons = []
    target_word = choose_target_word(user_id)  # брать из БД
    translate = translate_word()  # брать из БД
    target_word_btn = types.KeyboardButton(target_word)
    buttons.append(target_word_btn)
    others = choose_wrong_words()  # брать из БД
    other_words_btns = [types.KeyboardButton(word) for word in others]
    buttons.extend(other_words_btns)
    random.shuffle(buttons)
    next_btn = types.KeyboardButton(Command.NEXT)
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
    buttons.extend([next_btn, add_word_btn, delete_word_btn])

    markup.add(*buttons)

    greeting = f"Выбери перевод слова:\n🇷🇺 {translate}"
    bot.send_message(message.chat.id, greeting, reply_markup=markup)
    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['target_word'] = target_word
        data['translate_word'] = translate
        data['other_words'] = others


@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_card(message):
    """Функция вызывает выборку следующего слова через create_cards(message)"""
    create_cards(message)


@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def ask_word_to_delete(message):
    """Функция запрашивает слово у юзера для удаления"""
    session = Session()
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        cid = message.chat.id
        if (session.query(TargetWord.user_tg_id).filter(TargetWord.word == data['target_word']).first()) == (0,):
            bot.send_message(cid, f"""Ты можешь удалять только те слова, которые добавлены тобой. 
Продолжи угадывать слово: 🇷🇺'{data['translate_word']}' или нажми Дальше ⏭ для следующего слова""")
        else:
            bot.send_message(cid,
                             f"""Удалить слово "{show_target(data)}"? 
Напиши "Да" для удаления или нажми Дальше ⏭ для продолжения""")
            bot.register_next_step_handler(message, delete_word)
    session.close()


def delete_word(message):
    """Функция удаляет слово из БД"""
    user_id = message.chat.id
    user_answer = message.text
    session = Session()
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        if user_answer.strip().lower() == 'да':
            target_id = session.query(TargetWord.id).filter(
                and_(TargetWord.word == data['target_word'], TargetWord.user_tg_id == user_id)).first()
            if session.query(TargetWord.user_tg_id).filter(and_(TargetWord.word == data['target_word'],
                                                                TargetWord.user_tg_id != 0,
                                                                TargetWord.user_tg_id == user_id)).first() is not None:
                session.query(Translate).filter(Translate.target_word_id == target_id[0]).delete()
                session.commit()
                session.query(TargetWord).filter(
                    and_(TargetWord.word == data['target_word'], TargetWord.user_tg_id == user_id)).delete()
                session.commit()
                bot.send_message(message.chat.id, f"Слово успешно удалено. Нажми Дальше ⏭ ")

    session.close()


@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def ask_word_to_add(message):
    """Функция запрашивает слово у юзера для добавления"""
    cid = message.chat.id
    userStep[cid] = 1
    bot.send_message(cid, 'Введи слово, которое хочешь выучить и его перевод через пробел')
    bot.register_next_step_handler(message, add_word)


def add_word(message):
    """Функция добавляет слово в БД"""
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        user_id = message.from_user.id
        user_word = message.text
        session = Session()
        target_word = TargetWord(word=user_word.split()[0].title().strip(), user_tg_id=message.from_user.id)
        session.add(target_word)
        session.commit()
        target_id = session.query(TargetWord.id).filter(and_(TargetWord.word == user_word.split()[0].title().strip(),
                                                             TargetWord.user_tg_id == user_id)).first()[0]
        translate = Translate(translate=user_word.split()[1].title().strip(), target_word_id=target_id)
        session.add(translate)
        session.commit()
        session.close()
        bot.send_message(message.chat.id,
                         f"""Слово '{user_word.split()[0]}' успешно сохранено! 
Продолжи угадывать слово: 🇷🇺'{data['translate_word']}' или нажми Дальше ⏭ для следующего слова""")


@bot.message_handler(func=lambda message: True, content_types=['text'])
def message_reply(message):
    """Функция реагирует на выбор перевода слова и выводит пользователю угадал он его или нет"""
    text = message.text
    markup = types.ReplyKeyboardMarkup(row_width=2)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        target_word = data['target_word']
        if text == target_word:
            hint = show_target(data)
            hint_text = ["Отлично!❤", hint]
            hint = show_hint(*hint_text)
        else:
            for btn in buttons:
                if btn.text == text:
                    btn.text = text + '❌'
                    break
            hint = show_hint("Допущена ошибка!",
                             f"Попробуй ещё раз вспомнить слово 🇷🇺{data['translate_word']}")
    markup.add(*buttons)
    bot.send_message(message.chat.id, hint, reply_markup=markup)


if __name__ == '__main__':
    print('Start telegram bot...')
    bot.add_custom_filter(custom_filters.StateFilter(bot))
    bot.infinity_polling(skip_pending=True)
