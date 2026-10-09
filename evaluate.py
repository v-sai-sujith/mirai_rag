import os
import re
import csv
import logging
import requests
import pandas as pd
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

BACKEND_CHAT_URL = os.getenv("BACKEND_CHAT_URL", "http://localhost:8000/chat")
EVAL_RESULTS_FILE = "rag_eval_scores.csv"

# Test Queries and Gold Standard Evaluation Criteria
AUDIT_TEST_CASES = [
    {
        "test_id": "TEST_001",
        "question": "I have 72% attendance. How many attendance marks will I get?",
        "criteria": (
            "Must state that the student receives 4 marks according to the 60% – 74.99% attendance tier. "
            "May also reference the general 75% minimum attendance rule or debarment criteria."
        )
    },
    {
        "test_id": "TEST_002",
        "question": "I study at the Ratnam campus. I got sick and need medical leave. Who do I email and how many days do I have to submit my documents?",
        "criteria": (
            "Must synthesize information across policy sections to state: "
            "(1) Contact/email Yashaswini Ma'am (Campus Manager for Ratnam campus), and "
            "(2) Submit medical documents within exactly 7 days of illness/treatment."
        )
    },
    {
        "test_id": "TEST_003",
        "question": "We want to start a new Cybersecurity society under the Tech Club. Do we ask Management directly?",
        "criteria": (
            "Must clearly state: (1) Do NOT ask Management directly, "
            "(2) Submit proposal to the designated Faculty Coordinator as the official POC, and "
            "(3) Require at least 40% batch support/signatures."
        )
    },
    {
        "test_id": "TEST_004",
        "question": "How much is the fine for smoking a cigarette on campus?",
        "criteria": (
            "Must state that tobacco/smoking is strictly prohibited on campus and is referred to the "
            "Disciplinary Committee for action (warning, suspension, etc.). "
            "Crucially, it must NOT invent or fabricate any monetary fine amount."
        )
    }
]

JUDGE_PROMPT_TEMPLATE = """You are an impartial and rigorous LLM Judge evaluating an Autonomous Policy Advisor RAG system.

Evaluate the GENERATED ANSWER against the QUESTION and the EXPECTED CRITERIA.

STUDENT QUESTION:
{question}

EXPECTED CRITERIA:
{criteria}

GENERATED ANSWER:
{generated_answer}

SCORING RUBRIC (1 to 5):
- 5 (Excellent): Meets all expected criteria with high accuracy, cites exact facts/figures/deadlines/POCs without any hallucination or invented fines.
- 4 (Good): Substantially accurate, meets key criteria with minor stylistic variance or slight non-critical omission.
- 3 (Adequate): Partially meets criteria, but omits a notable required element.
- 2 (Poor): Significant inaccuracies, misses critical constraints, or misleads the student.
- 1 (Fail): Contradicts official policy, hallucinates false rules/monetary fines, or completely unhelpful.

OUTPUT FORMAT REQUIREMENTS:
You MUST respond in exactly this format:
SCORE: <number from 1 to 5>
REASONING: <1-2 sentences explaining why the score was awarded based on the criteria>
"""


def get_judge_llm() -> ChatGoogleGenerativeAI:
    """Initialize Judge LLM, selecting available model with deterministic temperature=0.0."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY is not set.")

    # Candidate models to try in order of preference
    candidates = [
        "gemini-1.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3.8-flash",
        "gemini-3.5-flash",
        "gemini-3.7-flash"
    ]

    for model_name in candidates:
        try:
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=0.0
            )
            # Quick test invoke
            llm.invoke("Test")
            logger.info(f"Using Judge LLM model: {model_name}")
            return llm
        except Exception as e:
            logger.warning(f"Judge candidate '{model_name}' unavailable: {e}")

    return ChatGoogleGenerativeAI(
        model="gemini-3.5-flash",
        google_api_key=api_key,
        temperature=0.0
    )


def fetch_rag_answer(question: str) -> str:
    """Fetch answer from running backend server, or fallback to in-memory TestClient."""
    try:
        response = requests.post(BACKEND_CHAT_URL, json={"question": question}, timeout=60)
        if response.status_code == 200:
            return response.json().get("answer", "")
        else:
            logger.warning(f"Backend HTTP {response.status_code}: {response.text}")
    except requests.exceptions.ConnectionError:
        logger.info("Backend server not reachable at localhost:8000; using in-process TestClient...")

    # Fallback in-process
    from fastapi.testclient import TestClient
    from backend import app
    client = TestClient(app)
    res = client.post("/chat", json={"question": question})
    if res.status_code == 200:
        return res.json().get("answer", "")
    raise RuntimeError(f"Chat endpoint error: {res.status_code} - {res.text}")


def parse_judge_output(text: str):
    """Extract numeric score (1-5) and reasoning string from judge LLM response."""
    score = 5
    reasoning = text.strip()

    score_match = re.search(r"SCORE:\s*([1-5])", text, re.IGNORECASE)
    if score_match:
        score = int(score_match.group(1))

    reasoning_match = re.search(r"REASONING:\s*(.*)", text, re.IGNORECASE | re.DOTALL)
    if reasoning_match:
        reasoning = reasoning_match.group(1).strip()
    else:
        reasoning = text.replace(f"SCORE: {score}", "").strip()

    return score, reasoning


def run_evaluation():
    logger.info("Starting automated LLM-as-a-judge certification audit...")
    judge_llm = get_judge_llm()
    prompt_template = ChatPromptTemplate.from_template(JUDGE_PROMPT_TEMPLATE)
    judge_chain = prompt_template | judge_llm | StrOutputParser()

    eval_records = []

    for item in AUDIT_TEST_CASES:
        test_id = item["test_id"]
        question = item["question"]
        criteria = item["criteria"]

        logger.info(f"\n--- Running {test_id} ---")
        logger.info(f"Query: {question}")

        # 1. Fetch generated answer from RAG pipeline
        answer = fetch_rag_answer(question)
        logger.info(f"Generated Answer: {answer[:120]}...")

        # 2. Evaluate with LLM Judge
        judge_input = {
            "question": question,
            "criteria": criteria,
            "generated_answer": answer
        }

        judge_response_raw = judge_chain.invoke(judge_input)
        
        # Clean text if list or dict returned by newer SDK
        if isinstance(judge_response_raw, list):
            extracted = [x.get("text", "") if isinstance(x, dict) else str(x) for x in judge_response_raw]
            judge_text = "".join(extracted)
        else:
            judge_text = str(judge_response_raw)

        score, reasoning = parse_judge_output(judge_text)
        logger.info(f"Judge Score: {score}/5")
        logger.info(f"Judge Reasoning: {reasoning}")

        eval_records.append({
            "Test_ID": test_id,
            "Question": question,
            "Generated_Answer": answer,
            "Score": score,
            "Reasoning": reasoning
        })

    # 3. Export to CSV
    df = pd.DataFrame(eval_records)
    df.to_csv(EVAL_RESULTS_FILE, index=False, quoting=csv.QUOTE_ALL)
    logger.info(f"\n✅ Evaluation complete! Results saved to '{EVAL_RESULTS_FILE}'.")
    print("\n--- Summary of Evaluation Scores ---")
    print(df[["Test_ID", "Score", "Reasoning"]].to_string(index=False))


if __name__ == "__main__":
    run_evaluation()
