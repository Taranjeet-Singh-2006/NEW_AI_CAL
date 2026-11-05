# AI Calculator

**AI Calculator — An Intelligent Mathematical Calculation and Problem-Solving Platform**

AI Calculator combines reliable everyday math tools with image-based and conversational assistance. Calculations that can be handled deterministically run locally in the Flask service; AI-assisted features use the Google Gemini API only from the server.

## Features

- Four primary areas: Core Calculation, AI-Based Calculation, Advanced Features, and History
- Normal and scientific calculators, shape formulas, linear and quadratic equation solving, unit conversions, and financial calculations
- Natural-language prompt and voice calculator support for common percentage, GST, circle-area, subtraction, and equation questions
- Optional AI solver, explanations, tutor, mistake review, and image math solving
- Function graphing, scenario comparison, multiple quadratic solution methods, savings projections, and a calculation dashboard
- SQLite-backed history with notes, search, filters, date ranges, per-entry deletion, and clear-all
- Responsive layout, keyboard-accessible controls, and light/dark theme

## Technology

- Python 3.11, Flask, Flask-SQLAlchemy, SQLAlchemy, SQLite
- HTML5, CSS3, JavaScript, Bootstrap 5, Plotly.js
- Optional Google Gemini API for AI explanations and image understanding

## Run locally on Windows

The project includes `START_LOCAL.bat` at the project root. Double-click it. The first run creates a local Python environment and installs the required packages.

If `.env` does not exist, the launcher creates it from `.env.example`. Add your Gemini key to `artifacts\ai-calculator\.env`:

```text
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.8-flash
```

Then double-click `START_LOCAL.bat` again. It starts Flask and opens:

`http://127.0.0.1:5000`

You can also run it manually from `artifacts/ai-calculator` with `python app.py`.

The SQLite database is created automatically at `database/calculator.db`.

## AI setup

AI-powered explanations, tutoring, mistake review, and image solving require an `GEMINI_API_KEY` environment secret. The key is read only by the Flask backend and is never sent to the browser. Without it, those routes return a clear unavailable message; core calculators and supported deterministic natural-language examples continue to work.

For local use, put `GEMINI_API_KEY` only in `artifacts\ai-calculator\.env`. The `.env` file is ignored by git. Never put a real key in frontend files or commit it. `GEMINI_MODEL` is optional and defaults to `gemini-3.8-flash`.

## Project structure

```text
app.py
models.py
services/
  ai_service.py
  calculator_service.py
  history_service.py
templates/
  index.html
static/
  app.js
  styles.css
database/
  calculator.db   # created on first run; ignored by version control
```

## Screenshots

Screenshots can be added here after the app is running.

## Future improvements

- Add authenticated, per-user calculation histories
- Add more unit categories and localization options
- Add richer symbolic math and downloadable solution reports