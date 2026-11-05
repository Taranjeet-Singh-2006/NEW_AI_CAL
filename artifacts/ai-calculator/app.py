import os
from datetime import datetime
import secrets

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from models import CalculationHistory, db
from services.ai_service import ai_available, solve, solve_image
from services.calculator_service import (
    CalculationError,
    calculate,
    evaluate_expression,
)
from services.history_service import (
    clear_history,
    dashboard_summary,
    delete_history_item,
    list_history,
    save_history,
)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

database_dir = os.path.join(BASE_DIR, "database")
os.makedirs(database_dir, exist_ok=True)
database_path = os.path.join(database_dir, "calculator.db")

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SESSION_SECRET") or secrets.token_urlsafe(32),
    SQLALCHEMY_DATABASE_URI=f"sqlite:///{database_path}",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SQLALCHEMY_ENGINE_OPTIONS={"connect_args": {"check_same_thread": False}},
    MAX_CONTENT_LENGTH=8 * 1024 * 1024,
)
db.init_app(app)


@app.get("/")
@app.get("/<path:page>")
def homepage(page=None):
    if page and page.startswith("calc-api/"):
        return jsonify({"error": "Not found."}), 404
    return render_template("index.html")


@app.get("/calc-api/status")
def status():
    return jsonify({
        "ai_available": ai_available(),
        "ai_provider": "Google Gemini",
        "model": os.environ.get("GEMINI_MODEL", "gemini-3.8-flash"),
    })


@app.post("/calc-api/calculate")
def calculate_route():
    payload = request.get_json(silent=True) or {}
    try:
        result = calculate(
            payload.get("calculator_type", ""),
            payload.get("inputs") or {},
            payload.get("expression", ""),
            payload.get("angle_mode", "degrees"),
        )
        result["category"] = payload.get("category") or "Core Calculation"
        result["calculator_type"] = payload.get("calculator_type", "")
        return jsonify(result)
    except CalculationError as error:
        return jsonify({"error": str(error)}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "Check the values and try again."}), 400


def _graph_function(expression):
    expression = expression.strip().replace("−", "-").replace("²", "^2")
    if "=" not in expression:
        evaluate_expression(expression, "radians", 0)
        return lambda x: evaluate_expression(expression, "radians", x), "y = " + expression

    left, right = [part.strip() for part in expression.split("=", 1)]
    # Convert a linear equation containing y into y = f(x), e.g. 5*x - 8*y + 1 = 0.
    if "y" not in expression.lower():
        raise CalculationError("For an equation graph, include y, for example 5*x - 8*y + 1 = 0.")
    normalized_left = left.replace("X", "x").replace("Y", "y")
    normalized_right = right.replace("X", "x").replace("Y", "y")
    combined = f"({normalized_left}) - ({normalized_right})"

    def eval_xy(x, y):
        # Solve only linear-in-y equations by evaluating the expression at y=0 and y=1.
        expr0 = combined.replace("y", "(0)")
        expr1 = combined.replace("y", "(1)")
        a0 = evaluate_expression(expr0, "radians", x)
        a1 = evaluate_expression(expr1, "radians", x)
        coef_y = a1 - a0
        if abs(coef_y) < 1e-12:
            raise CalculationError("The equation does not define y as a function of x.")
        return a0 + coef_y * y

    # Validate and determine the y coefficient once.
    test = eval_xy(0.0, 0.0)
    test1 = eval_xy(0.0, 1.0)
    coefficient = test1 - test
    if abs(coefficient) < 1e-12:
        raise CalculationError("The equation must contain y with a non-zero coefficient.")
    return lambda x: -eval_xy(x, 0.0) / coefficient, expression


@app.post("/calc-api/graph")
def graph_route():
    payload = request.get_json(silent=True) or {}
    expression = str(payload.get("expression", "")).strip()
    try:
        minimum = float(payload.get("xmin", -10))
        maximum = float(payload.get("xmax", 10))
        if minimum >= maximum:
            raise CalculationError("The x minimum must be smaller than the x maximum.")
        if maximum - minimum > 10000:
            raise CalculationError("Choose a graph range no wider than 10,000 units.")
        function, label = _graph_function(expression)
        points = []
        count = 241
        for index in range(count):
            x_value = minimum + (maximum - minimum) * index / (count - 1)
            try:
                y_value = function(x_value)
                if not (-1e15 < y_value < 1e15):
                    raise CalculationError("outside range")
                points.append({"x": x_value, "y": y_value})
            except CalculationError:
                points.append({"x": x_value, "y": None})
        table_points = [p for p in points if p["y"] is not None][::max(1, len(points) // 12)]
        return jsonify({"expression": expression, "label": label, "points": points, "table": table_points})
    except (CalculationError, TypeError, ValueError) as error:
        return jsonify({"error": str(error) or "Enter a valid function and range."}), 400


@app.post("/calc-api/ai/solve")
def ai_solve_route():
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify(solve(payload))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except RuntimeError as error:
        return jsonify({"error": str(error)}), 503


@app.post("/calc-api/ai/image")
def ai_image_route():
    try:
        result = solve_image(
            request.files.get("image"),
            request.form.get("mode", "detailed"),
            request.form.get("detail_level", "student"),
        )
        return jsonify(result)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except RuntimeError as error:
        return jsonify({"error": str(error)}), 503


@app.get("/calc-api/history")
def history_list_route():
    try:
        return jsonify({"items": list_history(request.args)})
    except ValueError as error:
        return jsonify({"error": str(error)}), 400


@app.post("/calc-api/history")
def history_create_route():
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify(save_history(payload)), 201
    except ValueError as error:
        return jsonify({"error": str(error)}), 400


@app.delete("/calc-api/history/<int:record_id>")
def history_delete_route(record_id):
    if not delete_history_item(record_id):
        return jsonify({"error": "That calculation was not found."}), 404
    return jsonify({"deleted": True, "id": record_id})


@app.delete("/calc-api/history")
def history_clear_route():
    deleted = clear_history()
    return jsonify({"deleted": deleted})


@app.get("/calc-api/dashboard")
def dashboard_route():
    return jsonify(dashboard_summary())


@app.errorhandler(413)
def upload_too_large(_error):
    return jsonify({"error": "Choose an image smaller than 8 MB."}), 413


@app.errorhandler(404)
def not_found(_error):
    if request.path.startswith("/calc-api/"):
        return jsonify({"error": "Not found."}), 404
    return render_template("index.html")


@app.errorhandler(500)
def internal_error(_error):
    db.session.rollback()
    if request.path.startswith("/calc-api/"):
        return jsonify({"error": "Something went wrong. Please try again."}), 500
    return render_template("index.html"), 500


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
