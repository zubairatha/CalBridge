"""
LLM Setup for Streamlined Agents
Using Ollama with llama3
"""
from langchain_ollama import OllamaLLM
from config import OLLAMA_BASE_URL, OLLAMA_MODEL

def get_llm():
    """Get configured Ollama LLM instance"""
    return OllamaLLM(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.7,
        top_p=0.9,
        num_predict=1024
    )

def get_llm_low_temp():
    """Get configured Ollama LLM instance with low temperature (for Task Difficulty Analyzer)"""
    return OllamaLLM(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.2,  # Low temperature for more deterministic output
        top_p=0.9,
        num_predict=256  # Shorter responses for JSON-only output
    )

def get_llm_decomposer():
    """Get configured Ollama LLM instance for LLM Decomposer (temp 0.3, compact output)"""
    return OllamaLLM(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.3,  # Low temperature for deterministic decomposition
        top_p=0.9,
        num_predict=384  # Compact JSON output for subtasks
    )

def test_llm():
    """Test the LLM connection"""
    try:
        llm = get_llm()
        response = llm.invoke("Hello! Can you respond with 'LLM is working'?")
        print(f"LLM Response: {response}")
        return True
    except Exception as e:
        print(f"LLM Test Failed: {e}")
        return False

if __name__ == "__main__":
    test_llm()
