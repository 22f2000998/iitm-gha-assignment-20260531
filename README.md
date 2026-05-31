# FastAPI Student API

## Install

```powershell
pip install -r requirements.txt
```

## Run

```powershell
uvicorn main:app --reload
```

## API endpoint

- All students: `http://127.0.0.1:8000/api`
- Filter by one class: `http://127.0.0.1:8000/api?class=1A`
- Filter by multiple classes: `http://127.0.0.1:8000/api?class=1A&class=1B`
- Batch sentiment: `http://127.0.0.1:8000/sentiment`

## Sentiment request example

```json
{
  "sentences": [
    "I love this product!",
    "This is terrible.",
    "The meeting is at 3 PM."
  ]
}
```
