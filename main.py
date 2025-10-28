from flask import Flask, render_template, request, redirect, url_for, session
# import os
import pandas as pd
import random

app = Flask(__name__)
app.secret_key = "secret-key"

# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# file_path = os.path.join(BASE_DIR, "question_quiz.xlsx")

URL_EXCEL = "https://docs.google.com/spreadsheets/d/1fyNknr77-Z4v7FhLEKb-_pNY-3cw4BSr/export?format=xlsx"

# ------------------ LOAD QUESTIONS ------------------


def load_questions():
    df = pd.read_excel(URL_EXCEL)
    questions = []
    for _, row in df.iterrows():
        options = [row["Correct"], row["Wrong_1"],
                   row["Wrong_2"], row["Wrong_3"]]
        random.shuffle(options)
        questions.append({
            "question": str(row["Question"]).strip(),
            "options": options,
            "correct": row["Correct"]
        })
    random.shuffle(questions)
    return questions


# ------------------ HOME ------------------
@app.route("/")
def home():
    """Trang chọn chế độ"""
    return render_template("home.html")


# ------------------ START ------------------
@app.route("/start/<mode>")
def start(mode):
    """Bắt đầu quiz"""
    session.clear()
    session["mode"] = mode  # exam hoặc practice
    session["score"] = 0
    session["q_index"] = 0
    session["questions"] = load_questions()
    session["answers"] = {}
    session["feedback"] = {}
    return redirect(url_for("question"))


# ------------------ GOTO (nhảy câu) ------------------
@app.route("/goto/<int:index>")
def goto(index):
    questions = session.get("questions", [])
    index = max(0, min(index, len(questions) - 1))
    session["q_index"] = index
    return redirect(url_for("question"))


# ------------------ QUESTION ------------------
@app.route("/question", methods=["GET", "POST"])
def question():
    questions = session.get("questions", [])
    q_index = int(session.get("q_index", 0))
    mode = session.get("mode", "exam")

    answers_raw = session.get("answers", {})
    feedback_raw = session.get("feedback", {})

    # ép key về int
    answers = {int(k): v for k, v in answers_raw.items()}
    feedback = {int(k): v for k, v in feedback_raw.items()}

    if request.method == "POST":
        nav = request.form.get("nav")
        user_answer = request.form.get("answer")

        # lưu đáp án
        if user_answer:
            answers[q_index] = user_answer
            session["answers"] = {str(k): v for k, v in answers.items()}

            # chế độ luyện tập => kiểm tra ngay
            if mode == "practice":
                correct = questions[q_index]["correct"]
                feedback[q_index] = (user_answer == correct)
                session["feedback"] = {str(k): v for k, v in feedback.items()}

            # chế độ thi => cộng điểm dần
            elif mode == "exam" and user_answer == questions[q_index]["correct"]:
                session["score"] = session.get("score", 0) + 1

        # điều hướng
        if nav == "next":
            session["q_index"] = q_index + 1
        elif nav == "back" and q_index > 0:
            session["q_index"] = q_index - 1
        elif nav == "home":
            return redirect(url_for("home"))

        return redirect(url_for("question"))

    # hết câu hỏi => sang kết quả
    # Hết câu hỏi
    if q_index >= len(questions):
        mode = session.get("mode", "exam")
        # Nếu là chế độ thi => sang kết quả
        if mode == "exam":
            return redirect(url_for("result"))
        # Nếu là chế độ luyện tập => hiển thị box "hoàn thành"
        else:
            return render_template(
                "done.html",
                total=len(questions)
            )

    question = questions[q_index]
    selected = answers.get(q_index, "")
    is_correct = feedback.get(q_index) if mode == "practice" else None

    # Thanh tiến độ: xanh nếu đúng, đỏ nếu sai, xám nếu chưa làm
    answers_status = []
    for i in range(len(questions)):
        if i in feedback and mode == "practice":
            if feedback[i]:
                answers_status.append("correct")
            else:
                answers_status.append("wrong")
        elif i in answers:
            answers_status.append("answered")
        else:
            answers_status.append("unanswered")

    return render_template(
        "index.html",
        question=question,
        q_index=q_index + 1,
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
    total = len(session.get("questions", []))
    mode = session.get("mode", "exam")
    return render_template("result.html", score=score, total=total, mode=mode)


if __name__ == "__main__":
    app.run(debug=True)
