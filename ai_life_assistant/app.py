# app.py
import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify, Response
from flask import stream_with_context
from pathlib import Path
import json
from flask_cors import CORS
import google.generativeai as genai

load_dotenv()
GEMINI_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GEMINI_KEY)   # configure client

app = Flask(__name__)
CORS(app)

MODEL_NAME = "gemini-1.5-flash"  # modern, fast text model
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

def generate(prompt: str) -> str:
    # simple wrapper with defensive error handling
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        resp = model.generate_content(prompt)
        return getattr(resp, "text", str(resp))
    except Exception as e:
        # surface concise error details for API clients
        return f"[Error from model: {e}]"

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "model": MODEL_NAME,
        "api_key_present": bool(GEMINI_KEY)
    })

@app.route("/summarize", methods=["POST"])
def summarize():
    text = request.json.get("text", "")
    prompt = f"Summarize the following text into clear bullet points:\n\n{text}"
    out = generate(prompt)
    return jsonify({"summary": out})

@app.route("/planner", methods=["POST"])
def planner():
    tasks = request.json.get("tasks", "")
    prompt = f"Create a prioritized daily plan for these tasks:\n\n{tasks}"
    out = generate(prompt)
    return jsonify({"plan": out})

@app.route("/rephrase", methods=["POST"])
def rephrase():
    text = request.json.get("text", "")
    prompt = f"Rephrase the following into three styles (formal, casual, concise):\n\n{text}"
    out = generate(prompt)
    return jsonify({"rephrased": out})

@app.route("/quote", methods=["POST"])
def quote():
    mood = request.json.get("mood", "")
    prompt = f"Give an original short motivational quote for someone feeling {mood}."
    out = generate(prompt)
    return jsonify({"quote": out})

def _to_chat_history(messages):
    # Convert simple [{'role': 'user'|'model', 'content': '...'}] to Gemini history format
    history = []
    for m in messages or []:
        role = m.get("role")
        content = m.get("content", "")
        if role in ("user", "model") and content:
            history.append({"role": role, "parts": [content]})
    return history

def _history_path(session_id: str) -> Path:
    sid = (session_id or "default").strip() or "default"
    return DATA_DIR / f"chat_{sid}.json"

def load_history(session_id: str = "default"):
    p = _history_path(session_id)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return []
    return []

def save_history(messages, session_id: str = "default"):
    p = _history_path(session_id)
    try:
        p.write_text(json.dumps(messages, ensure_ascii=False, indent=2))
    except Exception:
        pass

@app.route("/chat/history", methods=["GET"])
def chat_history():
    session_id = request.args.get("session_id", "default")
    return jsonify({"messages": load_history(session_id)})

@app.route("/chat", methods=["POST"])
def chat():
    payload = request.get_json(silent=True) or {}
    messages = payload.get("messages", [])
    session_id = payload.get("session_id", "default")

    # Minimal default greeting when no history
    if not messages:
        return jsonify({"reply": "Hi! I’m your AI assistant. How can I help today?"})

    try:
        last = messages[-1]
        if last.get("role") == "user":
            history = _to_chat_history(messages[:-1])
            prompt = last.get("content", "")
        else:
            history = _to_chat_history(messages)
            prompt = ""

        model = genai.GenerativeModel(MODEL_NAME)
        chat_session = model.start_chat(history=history)
        # Ensure we always send something
        to_send = prompt or "Please continue."
        resp = chat_session.send_message(to_send)
        text = getattr(resp, "text", str(resp))
        # Persist combined history (append the assistant reply)
        combined = messages + [{"role": "model", "content": text}]
        save_history(combined, session_id)
        return jsonify({"reply": text})
    except Exception as e:
        return jsonify({"reply": f"[Error from model: {e}]"}), 200

@app.route("/chat/stream", methods=["POST"])
def chat_stream():
    payload = request.get_json(silent=True) or {}
    messages = payload.get("messages", [])
    session_id = payload.get("session_id", "default")

    if not messages:
        def greet():
            yield "Hi! I’m your AI assistant. How can I help today?"
        return Response(stream_with_context(greet()), mimetype="text/plain")

    last = messages[-1]
    if last.get("role") == "user":
        history = _to_chat_history(messages[:-1])
        prompt = last.get("content", "")
    else:
        history = _to_chat_history(messages)
        prompt = ""

    model = genai.GenerativeModel(MODEL_NAME)
    chat_session = model.start_chat(history=history)
    to_send = prompt or "Please continue."

    def generate_stream():
        full = []
        try:
            for chunk in chat_session.send_message(to_send, stream=True):
                piece = getattr(chunk, "text", None)
                if piece:
                    full.append(piece)
                    yield piece
        except Exception as e:
            err = f"[Error from model: {e}]"
            yield err
            full.append(err)
        # On completion, persist
        try:
            reply = "".join(full)
            combined = messages + [{"role": "model", "content": reply}]
            save_history(combined, session_id)
        except Exception:
            pass

    return Response(stream_with_context(generate_stream()), mimetype="text/plain")

if __name__ == "__main__":
    # When debugging with VS Code, set debug=False to avoid the reloader spawn
    app.run(host="127.0.0.1", port=5000, debug=False)
