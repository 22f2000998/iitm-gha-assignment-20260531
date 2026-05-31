from csv import DictReader
from pathlib import Path
import re
from typing import List, Literal, Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

csv_path = Path(__file__).with_name("q-fastapi.csv")

app = FastAPI(title="Student API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

WORD_SCORES = {
    "amazing": 2.0,
    "awesome": 2.0,
    "awful": -2.0,
    "bad": -1.5,
    "beautiful": 1.5,
    "best": 2.0,
    "boring": -1.5,
    "brilliant": 2.0,
    "calm": 0.5,
    "cruel": -2.0,
    "delightful": 2.0,
    "disappointed": -2.0,
    "disappointing": -2.0,
    "enjoy": 1.5,
    "enjoyed": 1.5,
    "enjoying": 1.5,
    "excellent": 2.0,
    "excited": 1.5,
    "fantastic": 2.0,
    "fine": 0.5,
    "fun": 1.5,
    "glad": 1.5,
    "good": 1.5,
    "great": 2.0,
    "happy": 2.0,
    "hate": -2.0,
    "hated": -2.0,
    "helpful": 1.0,
    "horrible": -2.0,
    "joy": 1.5,
    "joyful": 1.5,
    "kind": 1.0,
    "love": 2.0,
    "loved": 2.0,
    "lovely": 1.5,
    "nice": 1.0,
    "okay": 0.5,
    "perfect": 2.0,
    "pleasant": 1.0,
    "poor": -1.5,
    "rough": -1.0,
    "sad": -2.0,
    "scared": -1.5,
    "stressful": -1.5,
    "super": 1.0,
    "terrible": -2.0,
    "terrific": 2.0,
    "tired": -1.0,
    "ugly": -1.5,
    "unhappy": -2.0,
    "upset": -2.0,
    "wonderful": 2.0,
    "worried": -1.5,
    "worst": -2.5,
}

PHRASE_SCORES = {
    "can't wait": 2.0,
    "do not like": -1.5,
    "fed up": -2.0,
    "feels bad": -1.5,
    "looking forward": 1.5,
    "not bad": 1.5,
    "not good": -1.5,
    "not great": -1.5,
    "not happy": -1.5,
    "not worth": -1.5,
    "really like": 1.5,
    "sick of": -2.0,
    "so happy": 2.0,
    "so proud": 1.5,
    "waste of time": -2.0,
    "works well": 1.5,
}

NEGATIONS = {
    "no",
    "not",
    "never",
    "none",
    "hardly",
    "scarcely",
    "cannot",
    "can't",
    "don't",
    "won't",
    "isn't",
    "wasn't",
}

INTENSIFIERS = {
    "absolutely": 1.8,
    "extremely": 1.8,
    "incredibly": 1.7,
    "really": 1.4,
    "so": 1.3,
    "too": 1.2,
    "totally": 1.6,
    "very": 1.5,
}

DIMINISHERS = {
    "a_bit": 0.7,
    "barely": 0.6,
    "fairly": 0.8,
    "kind_of": 0.7,
    "little": 0.8,
    "slightly": 0.7,
    "somewhat": 0.8,
}

class SentimentRequest(BaseModel):
    sentences: List[str]


class SentimentResult(BaseModel):
    sentence: str
    sentiment: Literal["happy", "sad", "neutral"]


class SentimentResponse(BaseModel):
    results: List[SentimentResult]


def load_students() -> List[dict]:
    with csv_path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = DictReader(csv_file)
        students = []
        for row in reader:
            students.append(
                {
                    "studentId": int(row["studentId"]),
                    "class": row["class"],
                }
            )
        return students


def analyze_sentiment(sentence: str) -> Literal["happy", "sad", "neutral"]:
    normalized_sentence = sentence.lower()
    phrase_score = sum(score for phrase, score in PHRASE_SCORES.items() if phrase in normalized_sentence)
    clauses = re.split(r"\b(?:but|however|though|although|yet)\b", normalized_sentence)
    contrast_matches = re.findall(r"\b(?:but|however|though|although|yet)\b", normalized_sentence)
    total_score = phrase_score

    for index, clause in enumerate(clauses):
        tokens = re.findall(r"[a-z']+", clause)
        clause_score = 0.0

        for token_index, token in enumerate(tokens):
            base_score = WORD_SCORES.get(token)
            if base_score is None:
                continue

            previous_tokens = tokens[max(0, token_index - 3):token_index]
            is_negated = any(previous in NEGATIONS for previous in previous_tokens)
            if is_negated:
                base_score *= -1

            multiplier = 1.0
            if token_index > 0:
                previous_token = tokens[token_index - 1]
                if previous_token in INTENSIFIERS:
                    multiplier *= INTENSIFIERS[previous_token]
                multiplier *= DIMINISHERS.get(previous_token, 1.0)
                if token_index > 1:
                    combined = f"{tokens[token_index - 2]}_{tokens[token_index - 1]}"
                    multiplier *= DIMINISHERS.get(combined, 1.0)

            clause_score += base_score * multiplier

        if index > 0 and contrast_matches:
            clause_score *= 1.35
        total_score += clause_score

    if "!" in sentence and total_score != 0:
        total_score *= 1.1
    if any(emoji in sentence for emoji in (":)", ":-)", ":d", "xd", "<3")):
        total_score += 1
    if any(emoji in sentence for emoji in (":(", ":-(", ":'(", "):")):
        total_score -= 1

    if total_score >= 0.75:
        return "happy"
    if total_score <= -0.75:
        return "sad"
    return "neutral"


STUDENTS = load_students()


@app.get("/api")
def get_students(class_: Optional[List[str]] = Query(default=None, alias="class")):
    if not class_:
        return {"students": STUDENTS}

    selected_classes = set(class_)
    filtered_students = [student for student in STUDENTS if student["class"] in selected_classes]
    return {"students": filtered_students}


@app.post("/sentiment", response_model=SentimentResponse)
def batch_sentiment(payload: SentimentRequest):
    results = [
        SentimentResult(sentence=sentence, sentiment=analyze_sentiment(sentence))
        for sentence in payload.sentences
    ]
    return SentimentResponse(results=results)
