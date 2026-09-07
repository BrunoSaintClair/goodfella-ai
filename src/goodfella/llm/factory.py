"""
Fábrica de Provedores de LLM .
"""

from langchain_core.language_models.chat_models import BaseChatModel

from goodfella.core.config import load_config
from goodfella.core.constants import DEFAULT_OLLAMA_MODEL

def get_llm() -> BaseChatModel:
    """
    Constrói e retorna a instância do modelo de linguagem (LangChain ChatModel)
    com base na configuração ativa global.
    Assegura que os modelos sejam instanciados com suporte a streaming 
    para uma melhor UX no terminal.
    """
    config = load_config()
    provider = str(config.get("provider", "Ollama")).lower()
    api_keys = config.get("api_keys", {})
    models = config.get("models", {})
    
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        api_key = api_keys.get("openai")
        if not api_key:
            raise ValueError("Chave de API da OpenAI não configurada. Edite o ~/.goodfella_config")
        model_name = models.get("openai", "gpt-4o")
        if not model_name or not isinstance(model_name, str):
            raise ValueError("Modelo da OpenAI inválido ou vazio. Verifique 'models' no ~/.goodfella_config")
        return ChatOpenAI(api_key=api_key, model=model_name, streaming=True)
        
    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        api_key = api_keys.get("gemini")
        if not api_key:
            raise ValueError("Chave de API do Gemini não configurada. Edite o ~/.goodfella_config")
        model_name = models.get("gemini", "gemini-1.5-pro")
        if not model_name or not isinstance(model_name, str):
            raise ValueError("Modelo do Gemini inválido ou vazio. Verifique 'models' no ~/.goodfella_config")
        return ChatGoogleGenerativeAI(google_api_key=api_key, model=model_name, streaming=True)
        
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        api_key = api_keys.get("anthropic")
        if not api_key:
            raise ValueError("Chave de API da Anthropic não configurada.")
        model_name = models.get("anthropic", "claude-3-5-sonnet-20240620")
        if not model_name or not isinstance(model_name, str):
            raise ValueError("Modelo da Anthropic inválido ou vazio. Verifique 'models' no ~/.goodfella_config")
        return ChatAnthropic(api_key=api_key, model_name=model_name, streaming=True)
        
    elif provider == "deepseek":
        from langchain_openai import ChatOpenAI
        api_key = api_keys.get("deepseek")
        if not api_key:
            raise ValueError("Chave de API do DeepSeek não configurada.")
        model_name = models.get("deepseek", "deepseek-coder")
        if not model_name or not isinstance(model_name, str):
            raise ValueError("Modelo do DeepSeek inválido ou vazio. Verifique 'models' no ~/.goodfella_config")
        return ChatOpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
            model=model_name,
            streaming=True
        )
        
    else:
        # Fallback: Ollama
        from langchain_ollama import ChatOllama
        model_name = models.get("ollama", DEFAULT_OLLAMA_MODEL)
        if not model_name or not isinstance(model_name, str):
            raise ValueError("Modelo do Ollama inválido ou vazio. Verifique 'models' no ~/.goodfella_config")
        return ChatOllama(model=model_name)
