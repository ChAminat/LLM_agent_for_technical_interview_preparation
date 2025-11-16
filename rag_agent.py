import json

from mistralai import Mistral
from langchain_community.retrievers import ArxivRetriever
from langchain_mistralai import ChatMistralAI
from langchain.embeddings.huggingface import HuggingFaceEmbeddings


from llama_index import VectorStoreIndex, SimpleDirectoryReader, ServiceContext
from llama_index.embeddings import LangchainEmbedding

mistral_api_key = ""
tavily_api_key = ""

docs=SimpleDirectoryReader(input_dir="/rag_data").load_data()

class RagAgent:
    def __init__(self, model: str = "mistral-small-latest"):
        self._client = Mistral(api_key=mistral_api_key)
        self._model = model

        self.llm = ChatMistralAI(
            model=model,
            max_retries=2,
            api_key=mistral_api_key
        )

        self.embed_model=LangchainEmbedding(HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2"))

        self.service_context = ServiceContext.from_defaults(
            chunk_size=1024,
            llm=self.llm,
            embed_model=self.embed_model
        )

        self.index=VectorStoreIndex.from_documents(docs, service_context=self.service_context)
        self.query_engine=self.index.as_query_engine()

    def set_user_info(self, name, interview_scope, difficulty):
        self.name = name
        self.interview_scope = interview_scope
        self.difficulty = difficulty

    def get_next_interview_question(self, question=""):
        prompt = f"Теперь ты выступаешь в роли системы-интревьюера, в которой хранится много вопросов с технических собеседований. \
          Задай мне вопрос из сферы {self.interview_scope} со сложностью {self.difficulty}. \
          Если возможно - приведи ПОДРОБНЫЙ ответ на этот вопрос, который ожидает интервьюер. \
          Будь максимально аккуратен и не добавляй лишний текст. \
          ФОРМАТ: json с полями question и answer. \
          Оставь в поле answer "", если у тебя нет ответа на заднный вопрос."
        
        question = question if question else prompt
        response = self.query_engine.query(question)
        json_response = json.load(response)

        question = json_response["question"]
        detailed_answer = get_detailed_answer(question)
        json_response["detailed_info"] = detailed_answer
        return json_response

    def check_answer_correctness(self, question, rag_answer, user_answer):
        prompt = f"Ты - эксперт IT в области {self.interview_scope}, который проверяет правильность \
                  и полноту ответов на вопросы собеседований. Тебе следует проверить, насколько качественный ответ для \
                  уровня сложности {self.difficulty} был дан пользователем на вопрос. Сравни ответ пользователя и ответ rag. \
                  Дай оценку, укажи на ошибки, если они есть, а затем приведи эталонный ответ на основе ответа rag и дополнительную \
                  справочную информацию, если она есть. \
                  ФОРМАТ ВХОДА: json с полями question, rag_answer, user_answer. \
                  ФОРМАТ ОТВЕТА: \
                  ОЦЕНКА \n\n НЕДОЧЕТЫ \n\n ПРАВИЛЬНЫЙ ОТВЕТ \n\n ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ"
        
        request = {"question": question, "rag_answer": rag_answer, "user_answer": user_answer}
                   
        response = self._client.chat.complete(
            model=self._model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": request}
            ]
        )

        return {
            "answer": response.choices[0].message.content,
            "contexts": [str(doc) for doc in docs]
        }

    def get_detailed_answer(self, question: str):
        retriever = ArxivRetriever(load_max_docs=2)
        docs = retriever.invoke(question)

        docs_text = "\n\n".join([doc.page_content for doc in docs])

        prompt = f"Ты - эксперт IT в области {self.interview_scope}, который подробно и \
                  и полно, дотупным языком отвечет на вопросы технических собеседований и дает справочную информацию.\
                  Твоя задача - дать полный развернутый ответ на задаваемый вопрос или дополнить ответ, если он уже есть в запросе.\
                  ФОРМАТ ОТВЕТА: \
                  КРАТКИЙ ОТВЕТ, КОТОРЫЙ УСТРОИТ ИНТЕРВЬЮЕРА \n\n ПОЛНЫЙ ОТВЕТ С ПОДРОБНЫМ ОБЪЯСНЕНИЕМ \
                  ## Docs {docs_text}"

        response = self._client.chat.complete(
            model=self._model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": question}
            ]
        )

        return {
            "answer": response.choices[0].message.content,
            "contexts": [str(doc) for doc in docs]
        }

rag_bot = RagAgent()