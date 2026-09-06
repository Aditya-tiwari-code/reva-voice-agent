import time
from typing import List, Dict, Any, Optional
from app.config import settings

class AdaptiveLLMRouter:
    """
    Cost-Aware Dynamic LLM Router.
    Routes simple queries to Groq Llama 3 (fast, low-cost) and
    complex queries to Gemini 1.5 Flash.
    """

    GROQ_MODEL = "llama3-8b-8192"
    GEMINI_MODEL = "gemini-1.5-flash"

    def __init__(self, groq_api_key: Optional[str] = None, gemini_api_key: Optional[str] = None):
        self.groq_api_key = groq_api_key or settings.GROQ_API_KEY
        self.gemini_api_key = gemini_api_key or settings.GEMINI_API_KEY

        self._groq_client = None
        self._gemini_client_initialized = False

    @property
    def groq_client(self):
        if self._groq_client is None and self.groq_api_key:
            try:
                from groq import Groq
                self._groq_client = Groq(api_key=self.groq_api_key)
            except Exception:
                self._groq_client = None
        return self._groq_client

    def _init_gemini(self):
        if not self._gemini_client_initialized and self.gemini_api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_api_key)
                self._gemini_client_initialized = True
            except Exception:
                pass

    def calculate_cost(self, model_used: str, tokens: int) -> float:
        """
        Calculates estimated cost in USD based on model token usage.
        - Groq Llama 3: ~$0.00008 per 1,000 tokens
        - Gemini Flash: ~$0.00015 per 1,000 tokens
        """
        if tokens <= 0:
            return 0.0

        if "groq" in model_used.lower() or "llama" in model_used.lower():
            rate_per_1k = 0.00008
        else:
            rate_per_1k = 0.00015

        return round((tokens / 1000.0) * rate_per_1k, 6)

    def route(self, text: str, complexity: str = "simple", context: str = "", history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Routes the prompt to Groq or Gemini based on complexity,
        constructs system prompt, measures latency, tokens, and cost.
        """
        history_str = str(history) if history else "[]"
        system_prompt = (
            "You are REVA, a multilingual real estate AI assistant. "
            "You help customers find properties in India. "
            "Always respond in the same language the customer used "
            "(Hindi, English, or mix). Be concise, friendly, and helpful.\n"
            "Use the provided property context to answer accurately.\n"
            f"Available properties context:\n{context}\n"
            f"Conversation history: {history_str}"
        )

        start_time = time.time()
        response_text = ""
        tokens_used = 0
        model_used_label = "groq_llama3" if complexity == "simple" else "gemini_flash"

        if complexity == "simple":
            # Groq Llama3
            if self.groq_client:
                try:
                    completion = self.groq_client.chat.completions.create(
                        model=self.GROQ_MODEL,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": text}
                        ],
                        temperature=0.7,
                        max_tokens=300
                    )
                    response_text = completion.choices[0].message.content
                    if hasattr(completion, "usage") and completion.usage:
                        tokens_used = completion.usage.total_tokens
                    else:
                        tokens_used = len((system_prompt + text + response_text).split())
                except Exception as e:
                    response_text = f"Fallback response: Found matching properties for '{text}' in context.\n{context}"
                    tokens_used = len((system_prompt + text + response_text).split())
            else:
                response_text = f"[Groq Mock Response]: Based on your request for '{text}', here are the matching properties:\n{context}"
                tokens_used = len((system_prompt + text + response_text).split())
        else:
            # Gemini Flash
            self._init_gemini()
            if self.gemini_api_key:
                try:
                    import google.generativeai as genai
                    model = genai.GenerativeModel(
                        model_name=self.GEMINI_MODEL,
                        system_instruction=system_prompt
                    )
                    response = model.generate_content(text)
                    response_text = response.text
                    if hasattr(response, "usage_metadata") and response.usage_metadata:
                        tokens_used = getattr(response.usage_metadata, "total_token_count", 0)
                    if tokens_used == 0:
                        tokens_used = len((system_prompt + text + response_text).split())
                except Exception as e:
                    response_text = f"Fallback response: Highly matching listings for complex query '{text}':\n{context}"
                    tokens_used = len((system_prompt + text + response_text).split())
            else:
                response_text = f"[Gemini Mock Response]: Detailed property details matching '{text}':\n{context}"
                tokens_used = len((system_prompt + text + response_text).split())

        latency_ms = round((time.time() - start_time) * 1000.0, 2)
        estimated_cost = self.calculate_cost(model_used_label, tokens_used)

        return {
            "response_text": response_text.strip(),
            "model_used": model_used_label,
            "tokens_used": tokens_used,
            "latency_ms": latency_ms,
            "estimated_cost_usd": estimated_cost
        }
