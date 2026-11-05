import base64
import json
import os
import re
import urllib.error
import urllib.request

from PIL import Image, ImageOps

from services.calculator_service import (
    CalculationError,
    format_number,
    solve_basic_word_problem,
    solve_equation,
)

MAX_IMAGE_BYTES = 8 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": "jpeg",
    "image/png": "png",
    "image/webp": "webp",
}
DEFAULT_MODEL = "gemini-3.8-flash"
DEFAULT_IMAGE_MODEL = "gemini-3.8-flash"


def ai_available():
    return bool(os.environ.get("GEMINI_API_KEY", "").strip())


def _mistake_check(prompt):
    problem_match = re.search(
        r"(?:problem|question)\s*:\s*(.+?)(?=\n\s*(?:my\s+(?:work|answer)|answer)\s*:|$)",
        prompt, re.IGNORECASE | re.DOTALL,
    )
    answer_match = re.search(
        r"(?:my\s+(?:work|answer)|answer)\s*:\s*(.+)",
        prompt, re.IGNORECASE | re.DOTALL,
    )
    if not problem_match or not answer_match or "=" not in problem_match.group(1):
        return None
    equation = problem_match.group(1).strip().splitlines()[0]
    try:
        solution = solve_equation(equation)
    except CalculationError:
        return None
    submitted = answer_match.group(1).strip()
    claimed_values = re.findall(r"x\s*=\s*(-?\d+(?:\.\d+)?)", submitted, re.IGNORECASE)
    if not claimed_values:
        return None
    correct_values = re.findall(r"x\s*=\s*(-?\d+(?:\.\d+)?)", solution["result"], re.IGNORECASE)
    is_correct = any(
        abs(float(claimed) - float(correct)) <= 1e-8
        for claimed in claimed_values for correct in correct_values
    )
    if is_correct:
        status = "Your answer appears to be correct."
        explanation = f"Substituting {claimed_values[0]} into the equation satisfies it."
    else:
        status = "Your answer appears to be incorrect."
        explanation = "Check the step where you move terms across the equals sign. Keep the equation balanced by performing the same operation on both sides."
    return {
        "answer": f"{status}\nCorrect answer: {solution['result']}",
        "interpreted_problem": equation,
        "calculation": "\n".join(solution["steps"]),
        "explanation": explanation,
    }


def _request_prompt(prompt, mode, detail_level, feature):
    task_instructions = {
        "mistake": "Check the student's work respectfully. State if the answer appears correct or incorrect, identify the first mistake, explain the correct approach, and give the correct answer.",
        "explain": "Explain the supplied mathematical problem at the requested level. Show valid steps and explain why each step is useful.",
        "tutor": "Act as a patient math tutor. Start with a useful hint or guiding question rather than giving away the final answer immediately, unless the learner explicitly asks for it.",
        "solver": "Solve the problem accurately. Show a clear step-by-step solution and a final answer.",
        "image": "Read the mathematical problem in the image, transcribe it, solve it accurately, show steps, and state a final answer.",
        "prompt": "Interpret the user's math question, show the relevant calculation, provide a concise explanation, and clearly state the result.",
        "voice": "Interpret the recognized speech as a math question, show the calculation, and clearly state the result.",
    }.get(feature, "Solve the mathematical question accurately and explain the result.")
    return (
        "You are a school mathematics teacher helping students in Classes 8 to 12. "
        "Your solution MUST look like the working an Indian school teacher writes on a notebook or blackboard. "
        "This is a strict formatting rule, not a suggestion. Use the simplest standard school method. "
        "Do NOT write long teaching paragraphs, motivational text, or advanced explanations unless the user explicitly asks for explanation. "
        "For algebra and equations, use LINE-BY-LINE NOTEBOOK WORKING. Put one mathematical transformation on each line and continue with '=' or the next equivalent equation. "
        "Example for 2x + 5 = 15: write exactly this style:\n2x + 5 = 15\n2x = 15 - 5\n2x = 10\nx = 10/2\nx = 5\n"
        "Do NOT replace this with sentences such as 'Subtract 5 from both sides' or 'Divide both sides by 2'. The algebraic line itself should show the operation. "
        "For quadratic equations, show school-level factorisation when suitable, one line at a time, for example: x² + 5x + 6 = 0, (x + 2)(x + 3) = 0, x + 2 = 0, x + 3 = 0, x = -2, x = -3. "
        "For trigonometry, use the standard school formula/identity and then substitute and simplify line by line. Example style:\ntan θ = 3/4\ntan θ = P/B\nP = 3\nB = 4\nH = √(P² + B²)\n  = √(3² + 4²)\n  = √25\n  = 5\nsin θ = P/H\n      = 3/5\n"
        "For trigonometric identities, show LHS first, simplify line by line, then RHS, and finish with 'Hence proved.' only when appropriate. "
        "For arithmetic, percentages, ratio, averages, profit/loss, simple interest, EMI, mensuration, geometry and similar school topics, use Formula → substitution → calculation → final value, with short lines rather than paragraphs. "
        "For word problems, use only the compact school structure when needed: Given, To Find, Formula, Substitution, Calculation, Answer. Keep each item short. "
        "For every mathematical solution, put the final numerical/algebraic answer on the last line. Avoid a separate long 'Final Answer' paragraph. A short 'Answer: x = 5' is acceptable when useful. "
        "Use PLAIN TEXT school notation by default. Do NOT use LaTeX delimiters such as $, $$, \\(, \\), \\[, \\]. Do NOT output commands such as \\frac, \\sqrt, \\text, \\left, \\right or Markdown code blocks. Use simple readable notation such as 1/2, √25, x², θ, × and ÷. "
        "For coordinate geometry, use this clean notebook order when relevant: PA² = PB², write the distance formula for both sides, substitute the coordinates, expand one side at a time, cancel common x² and y² terms, simplify line by line, and end with the required relation between x and y. Example structure: PA² = PB²\n(x-7)² + (y-1)² = (x-3)² + (y-5)²\nx² - 14x + 49 + y² - 2y + 1 = x² - 6x + 9 + y² - 10y + 25\n-14x - 2y + 50 = -6x - 10y + 34\nx - y = 2. Never dump a compressed expansion on one line. "
        "Never use code blocks for ordinary mathematical solutions. Never use programming-style syntax. Never use university-level methods unless the user explicitly asks for them. "
        "Check every arithmetic and algebraic step before answering. If the problem is ambiguous or an image is unclear, state what is unclear instead of guessing. "
        f"{task_instructions}\n"
        f"Requested answer style: {mode or 'short'}. Explanation level: {detail_level or 'school student'}. "
        "Regardless of the requested mode, keep the actual mathematical working at a clear Classes 8-12 school level.\n\n"
        f"User's question or work:\n{prompt}"
    )



def _clean_school_output(answer):
    """Normalize Gemini math output into readable school-notebook text.

    Gemini sometimes returns Markdown/LaTeX delimiters even when asked for plain
    school working. The UI should never show raw $, \\frac, \\text, etc.
    """
    if not answer:
        return answer
    text = str(answer).replace("\r\n", "\n").replace("\r", "\n").replace("\\n", "\n")
    # Remove fenced Markdown and emphasis markers.
    text = re.sub(r"```(?:text|latex|markdown)?", "", text, flags=re.IGNORECASE)
    text = text.replace("```", "").replace("**", "")
    # Strip math delimiters first.
    text = text.replace("\\[", "").replace("\\]", "")
    text = text.replace("\\(", "").replace("\\)", "")
    text = text.replace("$$", "").replace("$", "")

    # Convert common LaTeX constructs to simple school notation.
    def frac(m):
        return f"({m.group(1).strip()})/({m.group(2).strip()})"
    # Handle simple non-nested fractions repeatedly.
    for _ in range(3):
        text = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", frac, text)
    text = re.sub(r"\\sqrt\{([^{}]+)\}", r"√(\1)", text)
    text = re.sub(r"\\text\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\mathrm\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\left|\\right", "", text)
    text = re.sub(r"\\(?:cdot|times)", "×", text)
    text = re.sub(r"\\(?:div)", "÷", text)
    text = re.sub(r"\\pm", "±", text)
    text = re.sub(r"\\leq", "≤", text)
    text = re.sub(r"\\geq", "≥", text)
    text = re.sub(r"\\neq", "≠", text)
    text = re.sub(r"\\infty", "∞", text)
    text = re.sub(r"\\alpha", "α", text)
    text = re.sub(r"\\beta", "β", text)
    text = re.sub(r"\\theta", "θ", text)
    text = re.sub(r"\\pi", "π", text)
    # Common superscripts.
    text = re.sub(r"\^\{2\}", "²", text)
    text = re.sub(r"\^2", "²", text)
    text = re.sub(r"\^\{3\}", "³", text)
    text = re.sub(r"\^3", "³", text)
    # Remove leftover LaTeX command slashes but keep the command word readable.
    text = re.sub(r"\\([A-Za-z]+)", r"\1", text)
    # Normalize common OCR/AI formatting noise.
    text = text.replace("−", "-")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    # Do not allow huge blank gaps.
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def _gemini_error_message(status, detail):
    text = (detail or "").lower()
    if status == 401 or status == 403:
        return "Gemini rejected the API key or project. Check GEMINI_API_KEY in Replit Secrets."
    if status == 429:
        return "Gemini rate limit reached. Core calculators still work without AI; please try the AI feature again later."
    if status in (408, 504):
        return "Gemini took too long to respond. Please try the AI request again."
    if status >= 500:
        return "Gemini is temporarily unavailable. Please try the AI request again."
    if "not found" in text or status == 404:
        return "The configured Gemini model is not available for this API project."
    return "Gemini could not complete that request. Check the API key, model access, and request format."


def _extract_error(body):
    try:
        parsed = json.loads(body)
        return parsed.get("error", {}).get("message", "")
    except Exception:
        return body[:500]


def _call_gemini(text, image=None):
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("AI service is unavailable because GEMINI_API_KEY is not configured. Core Calculations still work.")

    model = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    parts = [{"text": text}]
    if image:
        mime_type, encoded = image
        parts.append({"inline_data": {"mime_type": mime_type, "data": encoded}})

    # Keep image requests deliberately simple. Some Gemini model/request combinations
    # are stricter about thinking configuration when multimodal input is present.
    generation_config = {"maxOutputTokens": 1200}
    if image is None:
        generation_config["thinkingConfig"] = {"thinkingLevel": "low"}
    payload = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": generation_config,
    }
    if image is not None:
        model = os.environ.get("GEMINI_IMAGE_MODEL", DEFAULT_IMAGE_MODEL).strip() or DEFAULT_IMAGE_MODEL
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    max_retries = 2
    base_delay = 1.5

    for attempt in range(max_retries + 1):
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            # A moderate timeout keeps the UI responsive while allowing normal model responses.
            with urllib.request.urlopen(request, timeout=35) as response:
                raw = response.read().decode("utf-8")
            data = json.loads(raw)
            candidates = data.get("candidates") or []
            if not candidates:
                raise RuntimeError("Gemini returned no answer. Please try again.")
            content = candidates[0].get("content", {})
            answer = "\n".join(
                part.get("text", "") for part in content.get("parts", [])
                if isinstance(part, dict) and part.get("text")
            ).strip()
            if not answer:
                raise RuntimeError("Gemini returned an empty answer. Please try again.")
            return answer
        except urllib.error.HTTPError as error:
            detail = _extract_error(error.read().decode("utf-8", errors="replace"))
            print(f"Gemini HTTP error {error.code} (attempt {attempt + 1}/{max_retries + 1}): {detail}")
            # Google recommends exponential backoff for transient 429/5xx errors.
            # Do not retry authentication, permission, malformed-request, or model errors.
            if error.code in (408, 429, 500, 502, 503, 504) and attempt < max_retries:
                import time
                time.sleep(base_delay * (2 ** attempt))
                continue
            raise RuntimeError(_gemini_error_message(error.code, detail)) from None
        except urllib.error.URLError as error:
            print(f"Gemini network error (attempt {attempt + 1}/{max_retries + 1}): {error.reason}")
            if attempt < max_retries:
                import time
                time.sleep(base_delay * (2 ** attempt))
                continue
            raise RuntimeError("Could not reach Gemini. Check your internet connection and try again.") from None
        except (TimeoutError, json.JSONDecodeError) as error:
            print(f"Gemini response error (attempt {attempt + 1}/{max_retries + 1}): {type(error).__name__}: {error}")
            if attempt < max_retries:
                import time
                time.sleep(base_delay * (2 ** attempt))
                continue
            raise RuntimeError("Gemini did not return a usable response. Please try again.") from None


def solve(payload):
    prompt = str(payload.get("prompt", "")).strip()
    if not prompt:
        raise ValueError("Enter a math question first.")
    if len(prompt) > 5000:
        raise ValueError("Please keep the question under 5,000 characters.")
    feature = str(payload.get("feature", "")).lower()

    if feature == "mistake":
        checked = _mistake_check(prompt)
        if checked:
            return checked
    if feature in {"prompt", "voice", "solver", ""}:
        deterministic = solve_basic_word_problem(prompt)
        if deterministic:
            return deterministic
    if not ai_available():
        raise RuntimeError("AI service is unavailable because GEMINI_API_KEY is not configured. Core Calculations still work.")

    answer = _call_gemini(_request_prompt(
        prompt,
        str(payload.get("mode", "short")),
        str(payload.get("detail_level", "student")),
        feature,
    ))
    return {"answer": _clean_school_output(answer), "interpreted_problem": None, "calculation": None, "explanation": None}


def solve_image(file_storage, mode, detail_level):
    if file_storage is None or not file_storage.filename:
        raise ValueError("Choose an image containing a math problem.")

    # Browsers occasionally report uploaded images as application/octet-stream or
    # omit the MIME type. Use the extension as a safe fallback instead of rejecting
    # an otherwise valid math image.
    mime_type = (file_storage.mimetype or "").lower().split(";", 1)[0]
    extension_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    if mime_type not in ALLOWED_IMAGE_TYPES:
        suffix = os.path.splitext(file_storage.filename.lower())[1]
        mime_type = extension_map.get(suffix, "")
    if mime_type not in ALLOWED_IMAGE_TYPES:
        raise ValueError("Use a JPEG, PNG, or WebP image.")

    contents = file_storage.read(MAX_IMAGE_BYTES + 1)
    if not contents:
        raise ValueError("The selected image is empty.")
    if len(contents) > MAX_IMAGE_BYTES:
        raise ValueError("Choose an image smaller than 8 MB.")

    # Normalize the uploaded image before sending it to Gemini. This handles
    # browser-generated PNG/WebP variants consistently and prevents malformed
    # MIME/content combinations from causing a generic API failure.
    try:
        from io import BytesIO
        with Image.open(BytesIO(contents)) as source:
            source = ImageOps.exif_transpose(source)
            if source.mode in ("RGBA", "LA", "P"):
                background = Image.new("RGB", source.size, "white")
                if source.mode == "P":
                    source = source.convert("RGBA")
                background.paste(source, mask=source.getchannel("A"))
                source = background
            else:
                source = source.convert("RGB")

            # Keep enough resolution for printed/handwritten equations without
            # sending unnecessarily large payloads.
            source.thumbnail((2200, 2200), Image.Resampling.LANCZOS)
            output = BytesIO()
            source.save(output, format="JPEG", quality=92, optimize=True)
            contents = output.getvalue()
        mime_type = "image/jpeg"
    except Exception as error:
        print(f"Image normalization error: {type(error).__name__}: {error}")
        raise ValueError("Could not read that image. Please upload a clear JPEG, PNG, or WebP image.") from None

    encoded = base64.b64encode(contents).decode("ascii")
    instruction = _request_prompt(
        "Read the mathematical problem in the attached image. First transcribe the problem exactly enough to preserve numbers, signs, powers, fractions, and symbols. Then solve it using the strict school-notebook working style. Do not guess any unclear symbol; state what is unclear.",
        mode, detail_level, "image"
    )
    answer = _call_gemini(instruction, (mime_type, encoded))
    return {"answer": _clean_school_output(answer), "interpreted_problem": None, "calculation": None, "explanation": None}

