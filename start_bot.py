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
    session = Session()
    kn_users = session.query(User.tg_id).all()
    session.close()
    return kn_users


def add_user(id):
    session = Session()
    if (id,) not in session.query(User.tg_id).all():
        id = User(tg_id=id)
        session.add(id)
        session.commit()
    session.close()


def choose_target_word(user_id):
    session = Session()
    choose_word = ''.join(*(session.query(TargetWord.word).join(TargetWord.user).
                            filter(or_(TargetWord.user_tg_id == 0, TargetWord.user_tg_id == user_id)).
                            order_by(func.random()).first()))
    global word_id
    word_id = session.query(Translate.id).join(Translate.target_word).filter(TargetWord.word == choose_word)[0]
    session.close()
    return choose_word


def translate_word():
    session = Session()
    translate = ''.join(*(session.query(Translate.translate).
                          join(Translate.target_word).filter(Translate.target_word_id == word_id[0]).first()))
    session.close()
    return translate


def show_hint(*lines):
    return '\n'.join(lines)


def show_target(data):
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
    user_id = message.from_user.id
    cid = message.chat.id
    if (user_id,) not in all_users():
        add_user(user_id)
        known_users.append(cid)
        userStep[cid] = 0
        bot.send_message(cid, "Hello, stranger, let study English...")
    markup = types.ReplyKeyboardMarkup(row_width=2)

    global buttons
    buttons = []
    target_word = choose_target_word(user_id)  # брать из БД
    translate = translate_word()  # брать из БД
    target_word_btn = types.KeyboardButton(target_word)
    buttons.append(target_word_btn)
    others = ['Green', 'White', 'Car']  # брать из БД
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
    create_cards(message)


@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        print(data['target_word'])  # удалить из БД


@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def ask_word(message):
    cid = message.chat.id
    userStep[cid] = 1
    bot.send_message(cid, 'Введите слово, которое хотите выучить и его перевод через пробел')
    bot.register_next_step_handler(message, add_word)


def add_word(message):
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
    text = message.text
    markup = types.ReplyKeyboardMarkup(row_width=2)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        target_word = data['target_word']
        if text == target_word:
            hint = show_target(data)
            hint_text = ["Отлично!❤", hint]
            # next_btn = types.KeyboardButton(Command.NEXT)
            # add_word_btn = types.KeyboardButton(Command.ADD_WORD)
            # delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
            # buttons.extend([next_btn, add_word_btn, delete_word_btn])
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
