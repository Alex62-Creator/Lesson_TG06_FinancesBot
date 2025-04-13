import asyncio
import random
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
# Файл config с ключами необходимо создавать дополнительно
from config import TOKEN, API_KEY_EXCHANGE
import sqlite3
import aiohttp
import logging
import requests

# Создаем объекты классов Bot (отвечает за взаимодействие с Telegram bot API) и Dispatcher (управляет обработкой входящих сообщений и команд)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Запускаем логирование
logging.basicConfig(level=logging.INFO)

# Создаем кнопки
button_registr = KeyboardButton(text="Регистрация в телеграм боте")
button_exchange_rates = KeyboardButton(text="Курс валют")
button_tips = KeyboardButton(text="Советы по экономии")
button_finances = KeyboardButton(text="Личные финансы")

# Создаем клавиатуру
keyboards = ReplyKeyboardMarkup(keyboard=[
    [button_registr, button_exchange_rates],
    [button_tips, button_finances]
    ], resize_keyboard=True)

# Создаем БД
conn = sqlite3.connect('user.db')
conn.row_factory = sqlite3.Row  # Теперь записи будут вести себя как словари
cursor = conn.cursor()

# Создаем таблицу в БД
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    telegram_id INTEGER UNIQUE,
    name TEXT,
    category1 TEXT,
    category2 TEXT,
    category3 TEXT,
    expenses1 REAL,
    expenses2 REAL,
    expenses3 REAL
    )
''')

conn.commit()

# Создаем класс FinancesForm для сохранения состояний
class FinancesForm(StatesGroup):
    category1 = State()
    expenses1 = State()
    category2 = State()
    expenses2 = State()
    category3 = State()
    expenses3 = State()

# Обработка команды /start
@dp.message(Command('start'))
async def send_start(message: Message):
    await message.answer("Привет! Я ваш личный финансовый помощник. Выберите одну из опций в меню:", reply_markup=keyboards)

# Обработка кнопки Регистрация
@dp.message(F.text == "Регистрация в телеграм боте")
async def registration(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    cursor.execute('''SELECT * FROM users WHERE telegram_id = ?''', (telegram_id,))
    user = cursor.fetchone()
    if user:
        await message.answer("Вы уже зарегистрированы!")
    else:
        await state.set_state(FinancesForm.category1)
        await message.reply(f"{message.from_user.first_name}, введите первую категорию расходов:")

# Добавление 1-й категории
@dp.message(FinancesForm.category1)
async def category1(message: Message, state: FSMContext):
    await state.update_data(category1 = message.text)
    await state.set_state(FinancesForm.category2)
    await message.reply("Введите вторую категорию расходов:")

# Добавление 2-й категории
@dp.message(FinancesForm.category2)
async def category2(message: Message, state: FSMContext):
    await state.update_data(category2 = message.text)
    await state.set_state(FinancesForm.category3)
    await message.reply("Введите третью категорию расходов:")

# Добавление 3-й категории и сохранение данных в БД
@dp.message(FinancesForm.category3)
async def category3(message: Message, state: FSMContext):
    await state.update_data(category3 = message.text)
    telegram_id = message.from_user.id
    name = message.from_user.full_name
    data = await state.get_data()
    cursor.execute('''INSERT INTO users (telegram_id, name,
                    category1, expenses1, category2, expenses2, category3,  expenses3) VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                   (telegram_id, name, data['category1'], 0, data['category2'], 0, data['category3'], 0))
    conn.commit()
    await state.clear()
    await message.answer("Вы успешно зарегистрированы!")

# Обработка кнопки Курсы валют
@dp.message(F.text == "Курс валют")
async def exchange_rates(message: Message):
    url = "https://v6.exchangerate-api.com/v6/09edf8b2bb246e1f801cbfba/latest/USD"
    url = f"https://v6.exchangerate-api.com/v6/{API_KEY_EXCHANGE}/latest/USD"
    try:
        response = requests.get(url)
        data = response.json()
        if response.status_code != 200:
            await message.answer("Не удалось получить данные о курсе валют!")
            return
        usd_to_rub = data['conversion_rates']['RUB']
        eur_to_usd = data['conversion_rates']['EUR']

        euro_to_rub = usd_to_rub / eur_to_usd

        await message.answer(f"1 USD - {usd_to_rub:.2f}  RUB\n"
                             f"1 EUR - {euro_to_rub:.2f}  RUB")

    except:
        await message.answer("Произошла ошибка")

# Обработка кнопки Советы
@dp.message(F.text == "Советы по экономии")
async def send_tips(message: Message):
    tips = [
        "Ведите бюджет и следите за своими расходами.",
        "Откладывайте часть доходов на сбережения.",
        "Покупайте товары по скидкам и распродажам.",
        "Ведите учет всех доходов и расходов, чтобы видеть полную картину финансов",
        "Устанавливайте лимиты на категории трат (еда, развлечения, транспорт)",
        "Планируйте бюджет на месяц вперед и придерживайтесь его",
        "Откладывайте минимум 10% от дохода на сбережения или инвестиции",
        "Избегайте спонтанных покупок — составляйте список перед походом в магазин",
        "Используйте кэшбэк и скидки, чтобы экономить на повседневных расходах",
        "Регулярно анализируйте траты и находите возможности для сокращения",
        "Создайте 'финансовую подушку' на случай непредвиденных ситуаций",
        "Откажитесь от ненужных подписок и услуг, которые не используете",
        "Ставьте финансовые цели (например, накопить на отпуск) и отслеживайте прогресс"
    ]
    tip = random.choice(tips)
    await message.answer(tip)

# Обработка кнопки Финансы
@dp.message(F.text == "Личные финансы")
async def finances(message: Message):
    telegram_id = message.from_user.id
    cursor.execute('''SELECT * FROM users WHERE telegram_id = ?''', (telegram_id,))
    user = cursor.fetchone()
    if user:
        await message.answer(f"Ваши категории расходов:\n"
                             f"/category1 ({user['category1']}) - {user['expenses1']}\n"
                             f"/category2 ({user['category2']}) - {user['expenses2']}\n"
                             f"/category3 ({user['category3']}) - {user['expenses3']}")
    else:
        await message.answer("Вы еще не зарегистрированы!")

# Обработка команды /category1
@dp.message(Command('category1'))
async def cat1(message: Message, state: FSMContext):
    await state.set_state(FinancesForm.expenses1)
    await message.reply(f"Введите потраченную сумму:")

# Добавление потраченной суммы к расходам по 1-й категории
@dp.message(FinancesForm.expenses1)
async def fin1(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    cursor.execute(
        '''UPDATE users SET expenses1 = expenses1 + ? WHERE telegram_id = ?''',
        (float(message.text), telegram_id))
    conn.commit()
    await state.clear()
    await message.answer(f"✅ Добавлено {float(message.text)} к расходам!")

# Обработка команды /category2
@dp.message(Command('category2'))
async def cat2(message: Message, state: FSMContext):
    await state.set_state(FinancesForm.expenses2)
    await message.reply(f"Введите потраченную сумму:")

# Добавление потраченной суммы к расходам по 2-й категории
@dp.message(FinancesForm.expenses2)
async def fin2(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    cursor.execute(
        '''UPDATE users SET expenses2 = expenses2 + ? WHERE telegram_id = ?''',
        (float(message.text), telegram_id))
    conn.commit()
    await state.clear()
    await message.answer(f"✅ Добавлено {float(message.text)} к расходам!")

# Обработка команды /category3
@dp.message(Command('category3'))
async def cat3(message: Message, state: FSMContext):
    await state.set_state(FinancesForm.expenses3)
    await message.reply(f"Введите потраченную сумму:")

# Добавление потраченной суммы к расходам по 3-й категории
@dp.message(FinancesForm.expenses3)
async def fin3(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    cursor.execute(
        '''UPDATE users SET expenses3 = expenses3 + ? WHERE telegram_id = ?''',
        (float(message.text), telegram_id))
    conn.commit()
    await state.clear()
    await message.answer(f"✅ Добавлено {float(message.text)} к расходам!")

# Обработка команды /help
@dp.message(Command('help'))
async def help(message: Message):
    telegram_id = message.from_user.id
    cursor.execute('''SELECT * FROM users WHERE telegram_id = ?''', (telegram_id,))
    user = cursor.fetchone()
    if user:
        await message.answer("Этот бот умеет выполнять дополнительные команды:\n"
                             "/start - приветствие\n"
                             "/help - список команд\n"
                             f"/category1 - добавление расходов по категории {user['category1']}\n"
                             f"/category2 - добавление расходов по категории {user['category2']}\n"
                             f"/category3 - добавление расходов по категории {user['category3']}")
    else:
        await message.answer("Этот бот умеет выполнять дополнительные команды:\n"
                             "/start - приветствие\n"
                             "/help - список команд\n"
                             f"/category1 - добавление расходов по категории 1"
                             f"/category2 - добавление расходов по категории 2"
                             f"/category3 - добавление расходов по категории 3")

# Создаем асинхронную функцию main, которая будет запускать наш бот
async def main():
    await dp.start_polling(bot)


# Запускаем асинхронную функцию main
if __name__ == '__main__':
    asyncio.run(main())