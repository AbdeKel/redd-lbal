"""
Redd Lbal API (FastAPI) - run on IBM LinuxONE:

    pip install fastapi uvicorn          # on s390x; if this fails use server/stdlib_server.py
    uvicorn server.app:app --host 0.0.0.0 --port 8000

Endpoints
  GET  /                 the web app (analysis done by this server)
  POST /api/check        {"text": "...", "sender": "+44...", "lang": "dar|fr|ar|en"}
  POST /api/batch        {"messages": ["...", {"text": "...", "sender": "..."}]}  (operators: bulk screening)
  GET  /api/radar        anonymous scam radar (differentially private counts + trending types)
  GET  /api/health       platform, version, model size
"""
from typing import List, Optional, Union

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from server.service import Service, page_html

svc = Service()
app = FastAPI(title="Redd Lbal API", version=svc.engine.b.get("version", "0"),
              description="Real-time scam detection for Moroccan messages (Darija, French, Arabic, English).")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])


class CheckIn(BaseModel):
    text: str = Field(..., max_length=5000, examples=["3afak sift liya 1500 dh daba f Wafacash, ana f mochkil"])
    sender: Optional[str] = Field(None, max_length=64, examples=["+44 7700 900123"])
    lang: str = Field("en", examples=["dar"])
    count: bool = Field(True, description="add one anonymous tick to the scam radar")


class BatchIn(BaseModel):
    messages: List[Union[str, dict]] = Field(..., max_length=10000)


class AnalyzeRequest(BaseModel):
    message: Optional[str] = Field(None, description="Message text")
    lien: Optional[str] = Field(None, description="Suspicious URL")
    sender: Optional[str] = Field(None, description="Sender")
    lang: Optional[str] = Field("fr", description="Language")


@app.get("/", response_class=HTMLResponse)
def index():
    return page_html()


@app.post("/api/check")
def check(body: CheckIn):
    return svc.check(body.text, body.sender, body.lang, body.count)


@app.post("/analyze")
def analyze(body: AnalyzeRequest):
    text = (body.message or "").strip()
    link = (body.lien or "").strip()
    if link and link not in text:
        text = f"{text} {link}".strip() if text else link
    return svc.check(text, body.sender, body.lang or "fr", count=True)


@app.post("/api/batch")
def batch(body: BatchIn):
    return svc.batch(body.messages)


@app.get("/api/radar")
def radar():
    return svc.radar.snapshot()


@app.get("/api/health")
def health():
    return svc.health()

