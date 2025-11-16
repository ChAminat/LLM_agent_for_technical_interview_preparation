import os
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from dotenv import load_dotenv
import json
import random

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY')

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в .env файле")
if not MISTRAL_API_KEY:
    raise ValueError("MISTRAL_API_KEY не найден в .env файле")

dp = Dispatcher()

interview_sessions = {}

class InterviewAgent:
    def __init__(self):
        self.base_url = "https://api.mistral.ai/v1"
        self.headers = {
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json"
        }
    
    async def start_interview(self, user_data: dict) -> str:
        """Начало интервью с представлением"""
        position = user_data.get('position', 'Data Science')
        level = user_data.get('level', 'Junior')
        name = user_data.get('name', '')
        
        # Локальный шаблон вместо вызова API для надежности
        welcome_templates = {
            "Data Science": {
                "Junior": f"Привет, {name}! Я ваш технический интервьюер по Data Science. Давайте начнем с основ: что такое машинное обучение и какие типы задач оно решает?",
                "Middle": f"Здравствуйте, {name}! Я технический интервьюер по Data Science. Начнем с вашего опыта: расскажите о самом сложном ML проекте, который вы реализовали?",
                "Senior": f"Добрый день, {name}! Я senior интервьюер по Data Science. Давайте обсудим архитектурные решения: как вы проектируете ML системы для масштабирования?"
            },
            "Machine Learning": {
                "Junior": f"Привет, {name}! Я интервьюер по Machine Learning. Первый вопрос: в чем разница между supervised и unsupervised learning?",
                "Middle": f"Здравствуйте, {name}! Я ML интервьюер. Расскажите о вашем опыте работы с нейронными сетями?",
                "Senior": f"Добрый день, {name}! Я senior ML инженер. Давайте обсудим оптимизацию моделей: какие методы вы используете для улучшения производительности?"
            },
            "Data Analysis": {
                "Junior": f"Привет, {name}! Я интервьюер по Data Analysis. Начнем с основ: какие инструменты для анализа данных вы используете?",
                "Middle": f"Здравствуйте, {name}! Я аналитик данных. Расскажите о вашем опыте создания дашбордов и отчетов?",
                "Senior": f"Добрый день, {name}! Я senior data analyst. Давайте обсудим подходы к A/B тестированию и анализу бизнес-метрик?"
            },
            "Software Engineering": {
                "Junior": f"Привет, {name}! Я интервьюер по Software Engineering. Первый вопрос: что такое ООП и основные принципы?",
                "Middle": f"Здравствуйте, {name}! Я software engineer. Расскажите о вашем опыте разработки архитектуры приложений?",
                "Senior": f"Добрый день, {name}! Я senior software engineer. Давайте обсудим микросервисную архитектуру и паттерны проектирования?"
            }
        }
        
        template = welcome_templates.get(position, welcome_templates["Data Science"])
        return template.get(level, template["Junior"])
    
    async def next_question(self, conversation_history: list, user_data: dict) -> str:
        """Следующий вопрос на основе истории"""
        position = user_data.get('position', 'Data Science')
        level = user_data.get('level', 'Junior')
        
        questions_db = {
            "Data Science": {
                "Junior": [
                    "Что такое переобучение (overfitting) и как с ним бороться?",
                    "Какие метрики оценки вы знаете для задач классификации?",
                    "Объясните разницу между pandas и numpy?",
                    "Что такое кросс-валидация и зачем она нужна?",
                    "Как вы работаете с пропущенными значениями в данных?"
                ],
                "Middle": [
                    "Расскажите о вашем опыте с feature engineering?",
                    "Как вы выбираете модели для конкретной бизнес-задачи?",
                    "Опишите процесс deployment ML модели?",
                    "Какие методы ensemble learning вы применяли?",
                    "Как вы оцениваете бизнес-impact ваших моделей?"
                ],
                "Senior": [
                    "Опишите архитектуру ML системы для реального продукта?",
                    "Как вы управляете technical debt в ML проектах?",
                    "Какие подходы к мониторингу ML моделей в production?",
                    "Как вы выстраиваете MLOps процессы в команде?",
                    "Расскажите о самом сложном technical challenge в вашей карьере?"
                ]
            },
            "Machine Learning": {
                "Junior": [
                    "В чем разница между bagging и boosting?",
                    "Что такое gradient descent?",
                    "Объясните принцип работы случайного леса?",
                    "Что такое regularization и зачем она нужна?",
                    "Какие алгоритмы кластеризации вы знаете?"
                ],
                "Middle": [
                    "Как работает attention mechanism в трансформерах?",
                    "Опишите процесс fine-tuning предобученных моделей?",
                    "Какие методы оптимизации нейронных сетей вы используете?",
                    "Как вы боретесь с gradient vanishing problem?",
                    "Расскажите о transfer learning на практике?"
                ],
                "Senior": [
                    "Архитектурные trade-offs при выборе моделей для production?",
                    "Как вы решаете проблему data drift в продакшене?",
                    "Оптимизация inference time больших моделей?",
                    "Подходы к explainable AI в сложных системах?",
                    "Управление lifecycle ML моделей в масштабе?"
                ]
            },
            "Data Analysis": {
                "Junior": [
                    "Какие инструменты для визуализации данных вы используете?",
                    "Как вы проводите очистку и предобработку данных?",
                    "Что такое SQL и основные операции?",
                    "Как вы работаете с выбросами в данных?",
                    "Какие типы графиков вы используете для разных задач?"
                ],
                "Middle": [
                    "Опишите процесс проведения A/B теста?",
                    "Как вы создаете и поддерживаете дашборды?",
                    "Какие методы прогнозирования вы используете?",
                    "Как вы приоритизируете аналитические задачи?",
                    "Расскажите о вашем опыте работы с большими данными?"
                ],
                "Senior": [
                    "Как вы выстраиваете data governance в компании?",
                    "Опишите архитектуру аналитической платформы?",
                    "Какие подходы к data quality assurance?",
                    "Как вы измеряете impact аналитических инициатив?",
                    "Расскажите о реализации сложных ETL процессов?"
                ]
            },
            "Software Engineering": {
                "Junior": [
                    "Что такое ООП и основные принципы?",
                    "Объясните разницу между классом и объектом?",
                    "Что такое REST API?",
                    "Какие структуры данных вы знаете?",
                    "Что такое Git и основные команды?"
                ],
                "Middle": [
                    "Опишите принципы SOLID?",
                    "Как вы проектируете архитектуру приложения?",
                    "Что такое микросервисы и их преимущества?",
                    "Какие паттерны проектирования вы используете?",
                    "Как вы обеспечиваете качество кода?"
                ],
                "Senior": [
                    "Как вы проектируете scalable systems?",
                    "Опишите подходы к performance optimization?",
                    "Как вы управляете technical debt?",
                    "Какие практики code review вы используете?",
                    "Расскажите о вашем опыте лидирования команд?"
                ]
            }
        }
        
        questions = questions_db.get(position, questions_db["Data Science"])
        level_questions = questions.get(level, questions["Junior"])
        
        session_questions = user_data.get("asked_questions", [])
        for question in level_questions:
            if question not in session_questions:
                if "asked_questions" not in user_data:
                    user_data["asked_questions"] = []
                user_data["asked_questions"].append(question)
                return question
        
        # Если все вопросы заданы
        return "Отлично! Мы обсудили основные темы. Хотите задать свой вопрос или завершить интервью?"
    
    async def ask_theory_question(self, user_question: str, user_data: dict) -> str:
        """Ответ на теоретический вопрос пользователя"""
        position = user_data.get('position', 'Data Science')
        
        try:
            messages = [
                {"role": "system", "content": f"Ты эксперт в {position}. Отвечай точно и понятно."},
                {"role": "user", "content": f"Вопрос: {user_question}\n\nДай развернутый ответ с примерами."}
            ]
            
            return await self._call_mistral(messages)
        except:
            fallback_answers = {
                "data science": "Data Science - это междисциплинарная область, объединяющая статистику, машинное обучение и анализ данных для извлечения знаний из данных.",
                "machine learning": "Machine Learning - это подраздел AI, focusing на разработке алгоритмов, которые могут обучаться на данных и делать предсказания.",
                "overfitting": "Переобучение возникает когда модель слишком хорошо учится на тренировочных данных, но плохо обобщает на новые данные. Методы борьбы: регуляризация, кросс-валидация, упрощение модели.",
                "cross validation": "Кросс-валидация - метод оценки модели, при котором данные разбиваются на k частей, модель тренируется на k-1 частях и валидируется на оставшейся. Повторяется k раз."
            }
            
            user_question_lower = user_question.lower()
            for key, answer in fallback_answers.items():
                if key in user_question_lower:
                    return answer
            
            return "Это интересный вопрос! Рекомендую изучить его подробнее в документации и специализированных ресурсах."
    
    async def analyze_answer(self, question: str, user_answer: str, user_data: dict) -> str:
        """Анализ ответа пользователя"""
        try:
            messages = [
                {"role": "system", "content": "Ты технический интервьюер. Дай конструктивную, но краткую обратную связь. Не испольуй Markdown форматирование."},
                {"role": "user", "content": f"Вопрос: {question}\nОтвет кандидата: {user_answer}\n\nПроанализируй ответ и дай feedback."}
            ]
            
            return await self._call_mistral(messages)
        except:
            answer_lower = user_answer.lower()
            feedback = "Спасибо за ответ! "
            
            if len(user_answer.split()) > 10:
                feedback += "Ваш ответ достаточно развернутый. "
            else:
                feedback += "Попробуйте давать более подробные ответы. "
            
            technical_terms = ["python", "sql", "ml", "algorithm", "model", "data", "analysis"]
            found_terms = [term for term in technical_terms if term in answer_lower]
            
            if found_terms:
                feedback += f"Вы упомянули важные термины: {', '.join(found_terms)}. "
            
            feedback += "Продолжайте в том же духе!"
            return feedback
    
    async def _call_mistral(self, messages) -> str:
        """Вызов Mistral API с обработкой ошибок"""
        try:
            async with aiohttp.ClientSession() as session:
                data = {
                    "model": "mistral-medium",
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 500
                }
                
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        return result["choices"][0]["message"]["content"]
                    else:
                        error_text = await response.text()
                        print(f"Mistral API Error: {response.status} - {error_text}")
                        return "Извините, временные технические трудности. Пожалуйста, продолжите с следующими вопросами."
                        
        except asyncio.TimeoutError:
            return "Время ожидания ответа истекло. Пожалуйста, попробуйте еще раз."
        except Exception as e:
            print(f"API call error: {e}")
            return "Произошла непредвиденная ошибка. Давайте продолжим с локальными вопросами."

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
        session["conversation_history"], 
        session["user_data"]
    )
    
    session["conversation_history"].append({"role": "interviewer", "content": next_question})
    session["current_question"] = next_question
    
    await message.answer(next_question, reply_markup=get_interview_keyboard())

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
        
        welcome_message = await interview_agent.start_interview(user_data)
        session["conversation_history"].append({"role": "interviewer", "content": welcome_message})
        session["current_question"] = welcome_message
        
        await message.answer(welcome_message, reply_markup=get_interview_keyboard())
    
    elif current_step == "awaiting_level_change":
        
        session["user_data"]["level"] = message.text
        session["step"] = "interview"
        session["user_data"]["asked_questions"] = []
        
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
        analysis = await interview_agent.analyze_answer(current_question, user_answer, session["user_data"])
        
        await message.answer(f"📝 Обратная связь:\n\n{analysis}")
        await message.answer("Используйте кнопки для продолжения:", reply_markup=get_interview_keyboard())
    
    elif current_step == "awaiting_question":
        user_question = message.text
        session["step"] = "interview"
        
        await message.answer("🔄 Ищу ответ на ваш вопрос...")
        answer = await interview_agent.ask_theory_question(user_question, session["user_data"])
        
        await message.answer(f"📚 Ответ на ваш вопрос:\n\n{answer}")
        await message.answer("Продолжаем интервью:", reply_markup=get_interview_keyboard())

async def main() -> None:
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())