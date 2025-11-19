import os
import asyncio
from typing import Any, Coroutine

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram import F
from aiogram.filters import Command
from aiogram.types import Message, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from dotenv import load_dotenv
import json
import random
from src.rag_agent import RagAgent
from llama_index import SimpleDirectoryReader
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY')

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в .env файле")
if not MISTRAL_API_KEY:
    raise ValueError("MISTRAL_API_KEY не найден в .env файле")

dp = Dispatcher()
docs = SimpleDirectoryReader(input_dir="rag_data").load_data()
interview_sessions = {}


class InterviewAgent:
    def __init__(self) -> None:
        print('Начало инициализации рага')
        self.rag_agent = RagAgent(docs, MISTRAL_API_KEY)
        print('Инициализация бота завершена')

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def get_question_reliable(self, message_history):
        return self.rag_agent.get_next_interview_question(message_history=message_history)

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def check_correctness_reliable(self, question, rag_ans, ans):
        return self.rag_agent.check_answer_correctness(question, rag_ans, ans)

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def get_answer_reliable(self, question, message_history):
        return self.rag_agent.get_detailed_answer(question, message_history)

    async def start_interview(self, user_data: dict) -> tuple[str, Any] | str:
        """Начало интервью с представлением"""
        position = user_data.get('position', 'Data Science')
        level = user_data.get('level', 'Junior')
        name = user_data.get('name', '')
        self.rag_agent.set_user_info(name, position, level)
        
        # Локальный шаблон вместо вызова API для надежности
        welcome_templates = {
            "Data Science": {
                "Junior": f"Привет, {name}! Я ваш технический интервьюер по Data Science. Начнем собеседование: ",
                "Middle": f"Здравствуйте, {name}! Я технический интервьюер по Data Science. Начнем собеседование: ",
                "Senior": f"Добрый день, {name}! Я senior интервьюер по Data Science. Начнем собеседование: "
            },
            "Machine Learning": {
                "Junior": f"Привет, {name}! Я интервьюер по Machine Learning. Начнем собеседование: ",
                "Middle": f"Здравствуйте, {name}! Я ML интервьюер. Начнем собеседование: ",
                "Senior": f"Добрый день, {name}! Я senior ML инженер. Начнем собеседование: "
            },
            "Data Analysis": {
                "Junior": f"Привет, {name}! Я интервьюер по Data Analysis. Начнем собеседование: ",
                "Middle": f"Здравствуйте, {name}! Я аналитик данных. Начнем собеседование: ",
                "Senior": f"Добрый день, {name}! Я senior data analyst. Начнем собеседование: "
            },
            "Software Engineering": {
                "Junior": f"Привет, {name}! Я интервьюер по Software Engineering. Начнем собеседование: ",
                "Middle": f"Здравствуйте, {name}! Я software engineer. Начнем собеседование: ",
                "Senior": f"Добрый день, {name}! Я senior software engineer. Начнем собеседование: "
            }
        }
        
        template = welcome_templates.get(position, welcome_templates["Data Science"])
        user_data["asked_questions"] = []
        question = await self.next_question(user_data, "")

        return template.get(level, template["Junior"]), question



    
    async def next_question(self, user_data: dict, message_history) -> Any | str:
        """Следующий вопрос на основе истории"""

        attempts = 500
        try:
            for _ in range(attempts):
                question = await self.get_question_reliable(message_history)
                if question['question'] not in user_data["asked_questions"]:
                    user_data["asked_questions"].append(question['question'])
                    return question
            else:
                return "Отлично! Мы обсудили основные темы. Хотите задать свой вопрос или завершить интервью?"
        except Exception as e:
            print(f"Все попытки не удались: {e}")
            return ("Произошла техническая ошибка! Проверьте подключение к интернету и попробуйте снова через "
                    "некоторое время")



    async def ask_theory_question(self, user_question: str, message_history: dict) -> str:
        """Ответ на теоретический вопрос пользователя"""
        try:
            answer = await self.get_answer_reliable(user_question, message_history)
            return answer

        except Exception as e:
            print(f"Все попытки не удались: {e}")
            return ("Произошла техническая ошибка! Проверьте подключение к интернету и попробуйте снова через "
                    "некоторое время")
    
    async def analyze_answer(self, question: dict, user_answer: str) -> str:
        """Анализ ответа пользователя"""
        try:
            analysis = await self.check_correctness_reliable(question['question'], question['answer'], user_answer)
            return analysis

        except Exception as e:
            print(f"Все попытки не удались: {e}")
            return ("Произошла техническая ошибка! Проверьте подключение к интернету и попробуйте снова через "
                    "некоторое время")

    async def change_settings(self, user_data: dict):
        position = user_data.get('position', 'Data Science')
        level = user_data.get('level', 'Junior')
        name = user_data.get('name', '')
        self.rag_agent.set_user_info(name, position, level)


interview_agent = InterviewAgent()

# Клавиатуры
def get_positions_keyboard():
    keyboard = ReplyKeyboardBuilder()
    positions = ["Data Science", "Machine Learning", "Data Analysis", "Software Engineering"]
    for position in positions:
        keyboard.add(KeyboardButton(text=position))
    return keyboard.as_markup(resize_keyboard=True)

def get_levels_keyboard():
    keyboard = ReplyKeyboardBuilder()
    levels = ["Junior", "Middle", "Senior"]
    for level in levels:
        keyboard.add(KeyboardButton(text=level))
    return keyboard.as_markup(resize_keyboard=True)

def get_interview_keyboard():
    keyboard = ReplyKeyboardBuilder()
    buttons = [
        "Следующий вопрос ➡️",
        "Задать вопрос ❓",
        "Сменить сложность 📊",
        "Сменить тему 🔄",
        "Закончить интервью 🏁"
    ]
    for button in buttons:
        keyboard.add(KeyboardButton(text=button))
    keyboard.adjust(2, 2, 1)  # Группируем кнопки по 2 в ряду
    return keyboard.as_markup(resize_keyboard=True)

def get_settings_keyboard():
    """Клавиатура для настроек"""
    keyboard = ReplyKeyboardBuilder()
    buttons = [
        "Сменить сложность 📊",
        "Сменить тему 🔄",
        "Назад к интервью ↩️"
    ]
    for button in buttons:
        keyboard.add(KeyboardButton(text=button))
    return keyboard.as_markup(resize_keyboard=True)

@dp.message(Command("start", "start_interview"))
async def start_interview_command(message: Message) -> None:
    """Начало процесса интервью"""
    user_id = message.from_user.id
    
    # Сброс сессии
    interview_sessions[user_id] = {
        "step": "awaiting_name",
        "conversation_history": [],
        "current_question": None,
        "user_data": {}
    }
    
    await message.answer(
        "🎯 Добро пожаловать на техническое собеседование!\n\n"
        "Давайте познакомимся. Как вас зовут?",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(F.text == "Следующий вопрос ➡️")
@dp.message(Command("next_question"))
async def next_question_handler(message: Message) -> None:
    """Следующий вопрос"""
    user_id = message.from_user.id
    
    if user_id not in interview_sessions or interview_sessions[user_id]["step"] != "interview":
        await message.answer("Сначала начните интервью командой /start")
        return
    
    session = interview_sessions[user_id]
    
    await message.answer("🔄 Формирую следующий вопрос...")
    
    next_question = await interview_agent.next_question(
        session["user_data"], session["conversation_history"]
    )
    
    session["conversation_history"].append({"role": "interviewer", "content": next_question})
    session["current_question"] = next_question

    if isinstance(next_question, str):
        await message.answer(next_question, reply_markup=get_interview_keyboard())
    else:
        await message.answer(next_question['question'], reply_markup=get_interview_keyboard())


@dp.message(F.text == "Задать вопрос ❓")
@dp.message(Command("ask_question"))
async def ask_question_handler(message: Message) -> None:
    """Запрос на вопрос по теории"""
    user_id = message.from_user.id
    
    if user_id not in interview_sessions:
        await message.answer("Сначала начните интервью командой /start")
        return
    
    interview_sessions[user_id]["step"] = "awaiting_question"
    await message.answer("Какой теоретический вопрос вас интересует?", reply_markup=ReplyKeyboardRemove())

@dp.message(F.text == "Сменить сложность 📊")
async def change_level_handler(message: Message) -> None:
    """Смена уровня сложности"""
    user_id = message.from_user.id
    
    if user_id not in interview_sessions:
        await message.answer("Сначала начните интервью командой /start")
        return
    
    interview_sessions[user_id]["step"] = "awaiting_level_change"
    await message.answer(
        "Выберите новый уровень сложности:",
        reply_markup=get_levels_keyboard()
    )

@dp.message(F.text == "Сменить тему 🔄")
async def change_position_handler(message: Message) -> None:
    """Смена темы/позиции"""
    user_id = message.from_user.id
    
    if user_id not in interview_sessions:
        await message.answer("Сначала начните интервью командой /start")
        return
    
    interview_sessions[user_id]["step"] = "awaiting_position_change"
    await message.answer(
        "Выберите новую тему для собеседования:",
        reply_markup=get_positions_keyboard()
    )

@dp.message(F.text == "Назад к интервью ↩️")
async def back_to_interview_handler(message: Message) -> None:
    """Возврат к интервью"""
    user_id = message.from_user.id
    
    if user_id not in interview_sessions:
        await message.answer("Сначала начните интервью командой /start")
        return
    
    interview_sessions[user_id]["step"] = "interview"
    session = interview_sessions[user_id]
    
    # Продолжаем с текущего вопроса или задаем новый
    current_question = session.get("current_question")
    if current_question:
        await message.answer(f"Продолжаем интервью!\n\nТекущий вопрос: {current_question}", 
                           reply_markup=get_interview_keyboard())
    else:
        await next_question_handler(message)

@dp.message(F.text == "Закончить интервью 🏁")
@dp.message(Command("finish"))
async def finish_interview_handler(message: Message) -> None:
    """Завершение интервью"""
    user_id = message.from_user.id
    
    if user_id not in interview_sessions:
        await message.answer("Интервью еще не начато")
        return
    
    user_data = interview_sessions[user_id].get("user_data", {})
    name = user_data.get("name", "Кандидат")
    position = user_data.get("position", "технический специалист")
    level = user_data.get("level", "")
    
    await message.answer(
        f"🎉 Спасибо, {name}!\n\n"
        f"Интервью на позицию {position} ({level}) завершено.\n"
        f"Для нового собеседования используйте /start",
        reply_markup=ReplyKeyboardRemove()
    )
    
    del interview_sessions[user_id]

@dp.message()
async def handle_all_messages(message: Message) -> None:
    """Обработка всех сообщений"""
    user_id = message.from_user.id
    
    if user_id not in interview_sessions:
        await message.answer("Для начала интервью используйте /start")
        return
    
    session = interview_sessions[user_id]
    current_step = session["step"]
    
    if current_step == "awaiting_name":
        session["user_data"]["name"] = message.text
        session["step"] = "awaiting_position"
        await message.answer(
            f"Приятно познакомиться, {message.text}!\n"
            f"Выберите сферу для собеседования:",
            reply_markup=get_positions_keyboard()
        )
    
    elif current_step == "awaiting_position":
        session["user_data"]["position"] = message.text
        session["step"] = "awaiting_level"
        await message.answer(
            f"Отлично! Сфера: {message.text}\n"
            f"Теперь выберите ваш уровень:",
            reply_markup=get_levels_keyboard()
        )
    
    elif current_step == "awaiting_level":
        session["user_data"]["level"] = message.text
        session["step"] = "interview"
        
        user_data = session["user_data"]
        await message.answer("🔄 Начинаем интервью...")
        
        template, question = await interview_agent.start_interview(user_data)
        welcome_message = template + question['question']
        session["conversation_history"].append({"role": "interviewer", "content": welcome_message})
        session["current_question"] = question
        
        await message.answer(welcome_message, reply_markup=get_interview_keyboard())
    
    elif current_step == "awaiting_level_change":
        
        session["user_data"]["level"] = message.text
        session["step"] = "interview"
        session["user_data"]["asked_questions"] = []
        await interview_agent.change_settings(session["user_data"])

        await message.answer(
            f"✅ Уровень сложности изменен на: {message.text}\n"
            f"Начинаем новую сессию вопросов...",
            reply_markup=get_interview_keyboard()
        )
        await next_question_handler(message)
    
    elif current_step == "awaiting_position_change":
        
        session["user_data"]["position"] = message.text
        session["step"] = "interview"
        session["user_data"]["asked_questions"] = []
        await interview_agent.change_settings(session["user_data"])
        
        await message.answer(
            f"✅ Тема изменена на: {message.text}\n"
            f"Начинаем новую сессию вопросов...",
            reply_markup=get_interview_keyboard()
        )
        await next_question_handler(message)
    
    elif current_step == "interview":
        user_answer = message.text
        current_question = session["current_question"]
        
        session["conversation_history"].append({"role": "candidate", "content": user_answer})
        
        await message.answer("🔄 Анализирую ваш ответ...")
        analysis = await interview_agent.analyze_answer(current_question, user_answer)

        session["conversation_history"].append({"role": "interviewer", "content": analysis})
        
        await message.answer(f"📝 Обратная связь:\n\n{analysis}")
        await message.answer("Используйте кнопки для продолжения:", reply_markup=get_interview_keyboard())
    
    elif current_step == "awaiting_question":
        user_question = message.text
        session["step"] = "interview"

        session["conversation_history"].append({"role": "candidate", "content": user_question})
        
        await message.answer("🔄 Ищу ответ на ваш вопрос...")
        answer = await interview_agent.ask_theory_question(user_question, session["conversation_history"])

        session["conversation_history"].append({"role": "interviewer", "content": answer})
        
        await message.answer(f"📚 Ответ на ваш вопрос:\n\n{answer}")
        await message.answer("Продолжаем интервью:", reply_markup=get_interview_keyboard())


async def main() -> None:
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

