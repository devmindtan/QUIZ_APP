from flask import Flask, render_template, request, redirect, url_for, session
import os
import random
import json
import uuid

app = Flask(__name__)
app.secret_key = "secret-key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ------------------ GLOBAL STORE ------------------
# Lưu câu hỏi tạm thời theo session_id
questions_store = {}

# ------------------ LOAD QUESTIONS ------------------


def load_questions(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    questions = []
    for item in data:
        options = [item["A"], item["B"], item["C"], item["D"]]
        correct_option = item[item["Answer"]]
        questions.append({
            "question": item["Question"].strip(),
            "options": options,
            "correct": correct_option
        })
    return questions

# ------------------ HOME ------------------


@app.route("/")
def home():
    assets_dir = os.path.join(BASE_DIR, "assets")
    assets_files = [f for f in os.listdir(assets_dir) if f.endswith(".json")]
    return render_template("home.html", files=assets_files)

# ------------------ START QUIZ ------------------


@app.route("/start/<mode>/<filename>")
def start(mode, filename):
    session.clear()
    session["mode"] = mode
    session["score"] = 0
    session["q_index"] = 0
    session["answers"] = {}
    session["feedback"] = {}
    session["file"] = filename

    # tạo session_id tạm
    session_id = str(uuid.uuid4())
    session["session_id"] = session_id

    # load file JSON được chọn
    file_path = os.path.join(BASE_DIR, "assets", filename)
    questions = load_questions(file_path)

    # trộn option và câu hỏi
    for q in questions:
        random.shuffle(q["options"])
    random.shuffle(questions)

    questions_store[session_id] = questions
    return redirect(url_for("question"))

# ------------------ GOTO ------------------


@app.route("/goto/<int:index>")
def goto(index):
    session_id = session.get("session_id")
    questions = questions_store.get(session_id, [])
    index = max(0, min(index, len(questions)-1))
    session["q_index"] = index
    return redirect(url_for("question"))

# ------------------ QUESTION ------------------


@app.route("/question", methods=["GET", "POST"])
def question():
    session_id = session.get("session_id")
    questions = questions_store.get(session_id, [])
    if not questions:
        return redirect(url_for("home"))

    q_index = int(session.get("q_index", 0))
    mode = session.get("mode", "exam")
    answers = {int(k): v for k, v in session.get("answers", {}).items()}
    feedback = {int(k): v for k, v in session.get("feedback", {}).items()}

    if request.method == "POST":
        nav = request.form.get("nav")
        user_answer = request.form.get("answer")

        if user_answer:
            answers[q_index] = user_answer
            session["answers"] = {str(k): v for k, v in answers.items()}

            if mode == "practice":
                correct = questions[q_index]["correct"]
                feedback[q_index] = (user_answer == correct)
                session["feedback"] = {str(k): v for k, v in feedback.items()}
            elif mode == "exam" and user_answer == questions[q_index]["correct"]:
                session["score"] = session.get("score", 0) + 1

        if nav == "next":
            session["q_index"] = q_index + 1
        elif nav == "back" and q_index > 0:
            session["q_index"] = q_index - 1
        elif nav == "home":
            return redirect(url_for("home"))

        return redirect(url_for("question"))

    # hết câu hỏi
    if q_index >= len(questions):
        # dọn bộ nhớ tạm
        questions_store.pop(session_id, None)
        if mode == "exam":
            return redirect(url_for("result"))
        else:
            return render_template("done.html", total=len(questions))

    question = questions[q_index]
    selected = answers.get(q_index, "")
    is_correct = feedback.get(q_index) if mode == "practice" else None

    # thanh tiến độ
    answers_status = []
    for i in range(len(questions)):
        if i in feedback and mode == "practice":
            answers_status.append("correct" if feedback[i] else "wrong")
        elif i in answers:
            answers_status.append("answered")
        else:
            answers_status.append("unanswered")

    return render_template(
        "index.html",
        question=question,
        q_index=q_index+1,
        total=len(questions),
        selected=selected,
        answers_status=answers_status,
        mode=mode,
        is_correct=is_correct
    )

# ------------------ RESULT ------------------


@app.route("/result")
def result():
    score = int(session.get("score", 0))
    session_id = session.get("session_id")
    questions = questions_store.get(session_id)
    if not questions:
        # fallback nếu session hết hạn
        filename = session.get("file")
        file_path = os.path.join(BASE_DIR, "assets", filename) if filename else os.path.join(
            BASE_DIR, "assets", "lich_su_dcs_vn.json")
        questions = load_questions(file_path)
    total = len(questions)
    mode = session.get("mode", "exam")
    return render_template("result.html", score=score, total=total, mode=mode)


# ------------------ RUN ------------------
if __name__ == "__main__":
    app.run(debug=True)
