import json

from mistralai import Mistral
from langchain_community.retrievers import ArxivRetriever
from langchain_mistralai import ChatMistralAI
from langchain_community.embeddings import HuggingFaceEmbeddings

from llama_index import VectorStoreIndex, ServiceContext
from llama_index.embeddings import LangchainEmbedding


class RagAgent:
    def __init__(self, docs, mistral_api_key: str, model: str = "mistral-small-latest"):
        print('внутри рага')
        self._client = Mistral(api_key=mistral_api_key)
        self._model = model
        print('1')

        self.llm = ChatMistralAI(
            model=model,
            max_retries=2,
            api_key=mistral_api_key
        )
        print('2')

        self.embed_model = LangchainEmbedding(HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2"))
        print('3')

        self.service_context = ServiceContext.from_defaults(
            chunk_size=1024,
            llm=self.llm,
            embed_model=self.embed_model
        )
        print('4')

        self.index=VectorStoreIndex.from_documents(docs, service_context=self.service_context)
        print('5')
        self.query_engine=self.index.as_query_engine()
        print('Инициализация рага завершена')

    def set_user_info(self, name, interview_scope, difficulty):
        self.name = name
        self.interview_scope = interview_scope
        self.difficulty = difficulty

    def get_detailed_answer(self, question: str, message_history=""):
        retriever = ArxivRetriever(load_max_docs=2)
        docs = retriever.invoke(question)

        docs_text = "\n\n".join([doc.page_content for doc in docs])

        prompt = f"""Ты - эксперт IT в области {self.interview_scope}, который подробно и \
                  и полно, доступным языком отвечает на вопросы технических собеседований и дает справочную информацию.\
                  Твоя задача - дать полный развернутый ответ на задаваемый вопрос или дополнить ответ, если он уже есть в запросе.\
                  Отвечай только на вопросы по теме собеседования!\

                  ФОРМАТ ОТВЕТА: ПОЛНЫЙ ОТВЕТ С ПОДРОБНЫМ ОБЪЯСНЕНИЕМ, КОТОРЫЙ УСТРОИТ ИНТЕРВЬЮЕРА \
                  Весь ответ должен быть дан на РУССКОМ языке (общеупотребимые термины сферы можно оставить на английском).\

                  ЗАМЕЧАНИЕ: Если тебя спросят на отвлеченную тему, вежливо ПРЕДЛОЖИ ВЕРНУТЬСЯ К СОБЕСЕДОВАНИЮ и расскажи про какую-нибудь другую полезную IT штуку, \
                  связанную с {self.interview_scope} \
                  (ВЕЖЛИВО ПРЕДЛОЖИ ВЕРНУТЬСЯ К СОБЕСЕДОВАНИЮ, а потом используй слова: Давайте я лучше расскажу вам про...) \
                  ## Docs {docs_text} \

                  Если для ответа на вопрос нужно обратиться к истории сообщений: \
                  ## Message_history {message_history}"""

        response = self._client.chat.complete(
            model=self._model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": question}
            ]
        )

        return response.choices[0].message.content

    def get_next_interview_question(self, question=""):
        prompt = f"Теперь ты выступаешь в роли системы-интервьюера, в которой хранится много вопросов с технических собеседований. \
          Задай мне вопрос из сферы {self.interview_scope} со сложностью {self.difficulty}. \
          Если возможно - приведи ПОДРОБНЫЙ, но ЛАКОНИЧНЫЙ ответ на этот вопрос, который ожидает интервьюер. \
          Будь максимально аккуратен и не добавляй лишний текст. \
          ФОРМАТ: json с полями question и answer. \
          Оставь в поле answer "", если у тебя нет ответа на заданный вопрос. \
          Вопрос нужно задать на РУССКОМ языке (общеупотребимые термины сферы можно оставить на английском)"
        
        question = question if question else prompt
        response = self.query_engine.query(question)
        clean_response = response.response.replace('```json', '').replace('```', '').strip()
        json_response = json.loads(clean_response)

        question = json_response["question"]
        answer = json_response["answer"]

        flag = 0 if answer != "" else 1
        if flag:
            max_attempts = 3
            for attempt in range(max_attempts):
                try:

                    detailed_answer = self.get_detailed_answer(question)
                    json_response["answer"] = detailed_answer
                    break

                except Exception as e:
                    print(f"Попытка {attempt + 1} не удалась: {e}")
                    if attempt == max_attempts - 1:
                        json_response["answer"] = "Не удалось получить ответ"
                        raise

        return json_response

    def check_answer_correctness(self, question, rag_answer, user_answer):
        prompt = f"Ты - эксперт IT в области {self.interview_scope}, который проверяет правильность \
                  и полноту ответов на вопросы собеседований. Тебе следует проверить, насколько качественный ответ для \
                  уровня сложности {self.difficulty} был дан пользователем на вопрос. Сравни ответ пользователя и ответ rag. \
                  Дай оценку, укажи на ошибки, если они есть, а затем приведи эталонный ответ на основе ответа rag и дополнительную \
                  справочную информацию, если она есть. \
                  ОБЯЗАТЕЛЬНО давай оценку так, как будто говоришь напрямую с учеником, обращаясь на вы. \
                  Окажи поддежку, если ответ неверный, но не забывай про здоровую критику. Похвали, если ответ верный. \
                  ФОРМАТ ВХОДА: json с полями question, rag_answer, user_answer. \
                  ФОРМАТ ОТВЕТА: \
                  ОЦЕНКА \n\n НЕДОЧЕТЫ \n\n ПРАВИЛЬНЫЙ ОТВЕТ \n\n ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ \
                  Весь ответ должен быть дан на РУССКОМ языке (общеупотребимые термины сферы можно оставить на английском)."
        
        request = f"""'question': {question}, 'rag_answer': {rag_answer}, 'user_answer': {user_answer}"""
                   
        response = self._client.chat.complete(
            model=self._model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": request}
            ]
        )

        return response.choices[0].message.content
