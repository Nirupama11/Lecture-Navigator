from __future__ import annotations

from typing import List, Dict
from loguru import logger

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig

from ..config import settings  # ✅ import your .env settings

# Try import provider-specific LLM wrapper (OpenAI)
try:
    from langchain_openai import ChatOpenAI
except Exception:  # pragma: no cover
    ChatOpenAI = None  # type: ignore


PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are a concise teaching assistant. Answer in ONE clear sentence. "
               "Use only the provided context snippets. Always append the most relevant timestamp(s) as citation(s) "
               "in the format [STARTs-ENDs]. If unsure, say you couldn't find a relevant timestamp."),
    ("human", "Question: {question}\n\nContext:\n{context}")
])


def build_context(results: List[Dict]) -> str:
    """
    Build a compact text context from the top results for the LLM.
    Limits to top 3 segments.
    """
    lines = []
    for r in (results or [])[:3]:
        start = int(r.get("start_time", 0))
        end = int(r.get("end_time", 0))
        ts = f"[{start}s-{end}s]"
        text = r.get("text", "").strip()
        lines.append(f"{ts} {text}")
    return "\n".join(lines)


async def generate_answer(question: str, results: List[Dict]) -> str:
    """
    Generate a concise one-sentence answer from `results` as context.
    Uses OpenAI if API key is configured, else falls back to snippet-based answer.
    """
    if not results:
        return "I couldn't find a relevant timestamp in the provided lectures."

    context = build_context(results)

    # Fallback if no OpenAI key is configured
    if not settings.OPENAI_API_KEY or ChatOpenAI is None or settings.LLM_MODEL.lower() == "none":
        snippet = results[0].get("text", "")
        first_sent = snippet.split(". ")[0].strip()[:200]
        ts = results[0].get("start_time")
        ts_str = f" [{int(ts)}s]" if ts is not None else ""
        logger.info("⚠️ Falling back to snippet answer (no LLM configured).")
        return f"{first_sent}{ts_str}"

    try:
        # ✅ Pass API key + model from settings
        llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=0.2,
            api_key=settings.OPENAI_API_KEY,
        )
        chain = PROMPT | llm

        if hasattr(chain, "ainvoke"):
            out = await chain.ainvoke(
                {"question": question, "context": context},
                config=RunnableConfig(max_concurrency=1),
            )
        else:
            out = chain.invoke(
                {"question": question, "context": context},
                config=RunnableConfig(max_concurrency=1),
            )

        content = getattr(out, "content", None) or (out if isinstance(out, str) else str(out))
        logger.info("✅ Answer generated using OpenAI LLM.")
        return content.strip()

    except Exception as e:
        logger.warning(f"❌ LLM call failed, using fallback snippet. error={e}")
        snippet = results[0].get("text", "")
        first_sent = snippet.split(". ")[0].strip()[:200]
        ts = results[0].get("start_time")
        ts_str = f" [{int(ts)}s]" if ts is not None else ""
        return f"{first_sent}{ts_str}"

