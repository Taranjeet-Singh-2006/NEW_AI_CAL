import ast
import math
import operator
import re


class CalculationError(ValueError):
    """Raised when an expression or calculator input is invalid."""


def _finite_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CalculationError("Enter a valid number.")
    value = float(value)
    if not math.isfinite(value):
        raise CalculationError("The result is outside the supported numeric range.")
    return value


def format_number(value):
    value = _finite_number(value)
    if abs(value) < 1e-12:
        value = 0.0
    return f"{value:,.10g}"


def _normalize_expression(expression):
    if not isinstance(expression, str) or not expression.strip():
        raise CalculationError("Enter a mathematical expression.")
    if len(expression) > 400:
        raise CalculationError("That expression is too long.")
    normalized = (
        expression.strip()
        .replace("×", "*")
        .replace("÷", "/")
        .replace("−", "-")
        .replace("π", "pi")
        .replace("√(", "sqrt(")
        .replace("^", "**")
    )
    normalized = re.sub(
        r"(\d+(?:\.\d+)?|\([^()]*\))\s*%",
        r"(\1/100)",
        normalized,
    )
    return normalized


def _functions(angle_mode):
    degrees = angle_mode == "degrees"

    def to_radians(value):
        return math.radians(value) if degrees else value

    def from_radians(value):
        return math.degrees(value) if degrees else value

    return {
        "sin": lambda value: math.sin(to_radians(value)),
        "cos": lambda value: math.cos(to_radians(value)),
        "tan": lambda value: math.tan(to_radians(value)),
        "asin": lambda value: from_radians(math.asin(value)),
        "acos": lambda value: from_radians(math.acos(value)),
        "atan": lambda value: from_radians(math.atan(value)),
        "sqrt": math.sqrt,
        "log": math.log10,
        "ln": math.log,
        "abs": abs,
        "exp": math.exp,
        "factorial": _factorial,
    }


def _factorial(value):
    number = _finite_number(value)
    if number < 0 or not number.is_integer() or number > 170:
        raise CalculationError("Factorial needs a whole number from 0 to 170.")
    return math.factorial(int(number))


_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}


def evaluate_expression(expression, angle_mode="degrees", x_value=None):
    normalized = _normalize_expression(expression)
    try:
        tree = ast.parse(normalized, mode="eval")
    except (SyntaxError, ValueError):
        raise CalculationError("Check the expression and try again.") from None

    functions = _functions(angle_mode)

    def visit(node):
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return _finite_number(node.value)
        if isinstance(node, ast.Name):
            constants = {"pi": math.pi, "e": math.e}
            if node.id in constants:
                return constants[node.id]
            if node.id == "x" and x_value is not None:
                return _finite_number(x_value)
            raise CalculationError(f"'{node.id}' is not a supported value.")
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
            left = visit(node.left)
            right = visit(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 100:
                raise CalculationError("Powers are limited to an exponent of 100.")
            try:
                return _finite_number(_BINARY_OPERATORS[type(node.op)](left, right))
            except ZeroDivisionError:
                raise CalculationError("Division by zero is not defined.") from None
            except (OverflowError, ValueError):
                raise CalculationError("That operation is outside the supported range.") from None
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            fn = functions.get(node.func.id)
            if fn is None or len(node.args) != 1 or node.keywords:
                raise CalculationError("Use a supported one-argument math function.")
            try:
                return _finite_number(fn(visit(node.args[0])))
            except CalculationError:
                raise
            except (ValueError, OverflowError, ZeroDivisionError):
                raise CalculationError("That function is not defined for this input.") from None
        raise CalculationError("Only standard arithmetic and supported math functions are allowed.")

    return visit(tree)


def _polynomial_from_ast(node):
    if isinstance(node, ast.Expression):
        return _polynomial_from_ast(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return [float(node.value), 0.0, 0.0]
    if isinstance(node, ast.Name) and node.id == "x":
        return [0.0, 1.0, 0.0]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        values = _polynomial_from_ast(node.operand)
        return values if isinstance(node.op, ast.UAdd) else [-item for item in values]
    if isinstance(node, ast.BinOp):
        left = _polynomial_from_ast(node.left)
        right = _polynomial_from_ast(node.right)
        if isinstance(node.op, ast.Add):
            return [left[i] + right[i] for i in range(3)]
        if isinstance(node.op, ast.Sub):
            return [left[i] - right[i] for i in range(3)]
        if isinstance(node.op, ast.Mult):
            result = [0.0, 0.0, 0.0]
            for left_power, left_value in enumerate(left):
                for right_power, right_value in enumerate(right):
                    power = left_power + right_power
                    if power > 2 and abs(left_value * right_value) > 1e-14:
                        raise CalculationError("Only linear and quadratic equations are supported.")
                    if power <= 2:
                        result[power] += left_value * right_value
            return result
        if isinstance(node.op, ast.Div) and abs(right[1]) < 1e-14 and abs(right[2]) < 1e-14:
            if abs(right[0]) < 1e-14:
                raise CalculationError("Division by zero is not defined.")
            return [item / right[0] for item in left]
        if isinstance(node.op, ast.Pow):
            exponent = _polynomial_from_ast(node.right)
            if any(abs(exponent[i]) > 1e-14 for i in (1, 2)) or exponent[0] not in (0, 1, 2):
                raise CalculationError("Equations may use x, x², and simple arithmetic only.")
            power = int(exponent[0])
            if power == 0:
                return [1.0, 0.0, 0.0]
            result = left
            if power == 2:
                result = _polynomial_from_ast(ast.BinOp(left=node.left, op=ast.Mult(), right=node.left))
            return result
    raise CalculationError("Use a linear or quadratic equation with the variable x.")


def _normalize_equation_side(side):
    side = side.strip().replace("−", "-").replace("²", "^2").replace("^", "**")
    side = re.sub(r"(?<=\d)\s*(?=x)", "*", side, flags=re.IGNORECASE)
    side = re.sub(r"(?<=\))\s*(?=[x\d(])", "*", side, flags=re.IGNORECASE)
    side = re.sub(r"(?<=x)\s*(?=\()", "*", side, flags=re.IGNORECASE)
    return side.replace("X", "x")


def solve_equation(equation):
    if not isinstance(equation, str) or "=" not in equation or len(equation) > 300:
        raise CalculationError("Enter an equation with an equals sign.")
    left_text, right_text = equation.split("=", 1)
    try:
        left = _polynomial_from_ast(ast.parse(_normalize_equation_side(left_text), mode="eval"))
        right = _polynomial_from_ast(ast.parse(_normalize_equation_side(right_text), mode="eval"))
    except (SyntaxError, ValueError):
        raise CalculationError("Use an equation such as 2x + 5 = 15 or x^2 + 5x + 6 = 0.") from None
    except RecursionError:
        raise CalculationError("That equation is too complex.") from None
    coefficients = [left[i] - right[i] for i in range(3)]
    return solve_coefficients(coefficients[2], coefficients[1], coefficients[0])



def solve_two_variable_equations(first, second):
    """Solve two linear equations in x and y using elimination."""
    def coefficients(equation):
        if not isinstance(equation, str) or "=" not in equation:
            raise CalculationError("Enter both equations with an equals sign.")
        left, right = equation.split("=", 1)
        left = left.strip().replace("−", "-").replace("²", "^2")
        right = right.strip().replace("−", "-").replace("²", "^2")
        # Support simple linear expressions such as 2x + 3y = 12.
        text = f"({left})-({right})"
        text = re.sub(r"(?<=\d)\s*(?=[xyXY])", "*", text)
        text = text.replace("X", "x").replace("Y", "y")
        def eval_at(x, y):
            expr = text.replace("x", f"({x})").replace("y", f"({y})")
            return evaluate_expression(expr, "radians")
        c = eval_at(0, 0)
        a = eval_at(1, 0) - c
        b = eval_at(0, 1) - c
        check = eval_at(2, 3)
        if abs(check - (c + 2*a + 3*b)) > 1e-8:
            raise CalculationError("Use linear equations in x and y, such as 2x + 3y = 12.")
        return a, b, -c

    a1, b1, c1 = coefficients(first)
    a2, b2, c2 = coefficients(second)
    determinant = a1*b2 - a2*b1
    if abs(determinant) < 1e-12:
        raise CalculationError("These equations do not have one unique x,y solution.")
    x = (c1*b2 - c2*b1) / determinant
    y = (a1*c2 - a2*c1) / determinant
    return {
        "result": f"x = {format_number(x)}\ny = {format_number(y)}",
        "formula": "Solve by elimination or substitution.",
        "steps": [
            f"Equation 1: {first}",
            f"Equation 2: {second}",
            f"Substitute/eliminate to get x = {format_number(x)}.",
            f"Then substitute x back to get y = {format_number(y)}.",
        ],
    }

def solve_coefficients(a, b, c):
    a, b, c = (_finite_number(a), _finite_number(b), _finite_number(c))
    if abs(a) < 1e-14:
        if abs(b) < 1e-14:
            if abs(c) < 1e-14:
                raise CalculationError("Every value of x satisfies this equation.")
            raise CalculationError("This equation has no solution.")
        root = -c / b
        return {
            "result": f"x = {format_number(root)}",
            "formula": f"{format_number(b)}x + {format_number(c)} = 0",
            "steps": [
                f"Move the constant term: {format_number(b)}x = {format_number(-c)}.",
                f"Divide both sides by {format_number(b)}.",
                f"x = {format_number(root)}.",
            ],
        }
    discriminant = b * b - 4 * a * c
    denominator = 2 * a
    if discriminant >= 0:
        root_one = (-b + math.sqrt(discriminant)) / denominator
        root_two = (-b - math.sqrt(discriminant)) / denominator
        result = f"x = {format_number(root_one)}"
        if abs(root_one - root_two) > 1e-12:
            result += f"\nx = {format_number(root_two)}"
        roots_text = f"{format_number(root_one)} and {format_number(root_two)}"
        last_step = f"The solutions are x = {format_number(root_one)} and x = {format_number(root_two)}."
    else:
        real = -b / denominator
        imaginary = math.sqrt(-discriminant) / abs(denominator)
        result = f"x = {format_number(real)} ± {format_number(imaginary)}i"
        roots_text = result
        last_step = f"The complex solutions are {result}."
    return {
        "result": result,
        "formula": "Quadratic formula: x = (−b ± √(b² − 4ac)) / 2a",
        "steps": [
            f"Identify a = {format_number(a)}, b = {format_number(b)}, and c = {format_number(c)}.",
            f"Calculate the discriminant: b² − 4ac = {format_number(discriminant)}.",
            f"Substitute into the quadratic formula; the roots are {roots_text}.",
            last_step,
        ],
    }


def _required(inputs, name, label):
    try:
        value = _finite_number(float(inputs[name]))
    except (KeyError, TypeError, ValueError):
        raise CalculationError(f"Enter a valid {label}.") from None
    return value


def calculate_shape(inputs):
    shape = str(inputs.get("shape", "")).lower()
    if shape == "circle":
        radius = _required(inputs, "radius", "radius")
        if radius < 0:
            raise CalculationError("Radius cannot be negative.")
        return {
            "result": f"Area: {format_number(math.pi * radius ** 2)}\nCircumference: {format_number(2 * math.pi * radius)}",
            "formula": "Area = πr² · Circumference = 2πr",
            "steps": [f"Substitute radius r = {format_number(radius)} into both formulas."],
        }
    if shape == "square":
        side = _required(inputs, "side", "side length")
        if side < 0:
            raise CalculationError("Side length cannot be negative.")
        return {
            "result": f"Area: {format_number(side ** 2)}\nPerimeter: {format_number(4 * side)}",
            "formula": "Area = s² · Perimeter = 4s",
            "steps": [f"Substitute side s = {format_number(side)}."],
        }
    if shape == "rectangle":
        length = _required(inputs, "length", "length")
        width = _required(inputs, "width", "width")
        if min(length, width) < 0:
            raise CalculationError("Side lengths cannot be negative.")
        return {
            "result": f"Area: {format_number(length * width)}\nPerimeter: {format_number(2 * (length + width))}",
            "formula": "Area = length × width · Perimeter = 2(length + width)",
            "steps": [f"Substitute length {format_number(length)} and width {format_number(width)}."],
        }
    if shape == "triangle":
        base = _required(inputs, "base", "base")
        height = _required(inputs, "height", "height")
        if min(base, height) < 0:
            raise CalculationError("Triangle dimensions cannot be negative.")
        area = base * height / 2
        result = f"Area: {format_number(area)}"
        formula = "Area = ½ × base × height"
        steps = [f"Area = ½ × {format_number(base)} × {format_number(height)} = {format_number(area)}."]
        try:
            sides = [_required(inputs, key, f"side {key[-1]}") for key in ("side_a", "side_b", "side_c")]
        except CalculationError:
            sides = []
        if len(sides) == 3 and all(side >= 0 for side in sides):
            if max(sides) >= sum(sides) - max(sides):
                raise CalculationError("The side lengths do not form a valid triangle.")
            result += f"\nPerimeter: {format_number(sum(sides))}"
            formula += " · Perimeter = a + b + c"
        return {"result": result, "formula": formula, "steps": steps}
    if shape == "cylinder":
        radius = _required(inputs, "radius", "radius")
        height = _required(inputs, "height", "height")
        if min(radius, height) < 0:
            raise CalculationError("Cylinder dimensions cannot be negative.")
        return {
            "result": f"Volume: {format_number(math.pi * radius ** 2 * height)}\nSurface area: {format_number(2 * math.pi * radius * (radius + height))}",
            "formula": "Volume = πr²h · Surface area = 2πr(r + h)",
            "steps": [f"Substitute r = {format_number(radius)} and h = {format_number(height)}."],
        }
    if shape == "sphere":
        radius = _required(inputs, "radius", "radius")
        if radius < 0:
            raise CalculationError("Radius cannot be negative.")
        return {
            "result": f"Volume: {format_number(4 * math.pi * radius ** 3 / 3)}\nSurface area: {format_number(4 * math.pi * radius ** 2)}",
            "formula": "Volume = ⁴⁄₃πr³ · Surface area = 4πr²",
            "steps": [f"Substitute radius r = {format_number(radius)}."],
        }
    raise CalculationError("Choose a supported shape.")


UNIT_GROUPS = {
    "length": {
        "meters": 1.0, "kilometers": 1000.0, "centimeters": 0.01,
        "miles": 1609.344, "feet": 0.3048, "inches": 0.0254,
    },
    "weight": {"grams": 1.0, "kilograms": 1000.0, "pounds": 453.59237},
    "area": {"square_meters": 1.0, "square_kilometers": 1_000_000.0, "square_feet": 0.09290304},
    "volume": {"liters": 1.0, "milliliters": 0.001, "cubic_meters": 1000.0},
    "speed": {"meters_per_second": 1.0, "kilometers_per_hour": 1 / 3.6, "miles_per_hour": 0.44704},
}


def _to_celsius(value, unit):
    if unit == "celsius":
        return value
    if unit == "fahrenheit":
        return (value - 32) * 5 / 9
    if unit == "kelvin":
        return value - 273.15
    raise CalculationError("Choose a supported temperature unit.")


def _from_celsius(value, unit):
    if unit == "celsius":
        return value
    if unit == "fahrenheit":
        return value * 9 / 5 + 32
    if unit == "kelvin":
        return value + 273.15
    raise CalculationError("Choose a supported temperature unit.")


def convert_unit(inputs):
    value = _required(inputs, "value", "value")
    source = str(inputs.get("from_unit", "")).lower()
    target = str(inputs.get("to_unit", "")).lower()
    if source in {"celsius", "fahrenheit", "kelvin"} and target in {"celsius", "fahrenheit", "kelvin"}:
        converted = _from_celsius(_to_celsius(value, source), target)
        category = "Temperature"
    else:
        matching_group = next(
            (units for units in UNIT_GROUPS.values() if source in units and target in units),
            None,
        )
        if matching_group is None:
            raise CalculationError("Choose units from the same supported category.")
        converted = value * matching_group[source] / matching_group[target]
        category = next(name.title() for name, units in UNIT_GROUPS.items() if units is matching_group)
    return {
        "result": f"{format_number(value)} {source.replace('_', ' ')} = {format_number(converted)} {target.replace('_', ' ')}",
        "formula": f"{category} conversion",
        "steps": [f"Converted {format_number(value)} {source.replace('_', ' ')} to {format_number(converted)} {target.replace('_', ' ')}."],
    }


def calculate_financial(inputs):
    kind = str(inputs.get("financial_type", "percentage")).lower()
    if kind == "percentage":
        value = _required(inputs, "value", "base amount")
        rate = _required(inputs, "rate", "percentage")
        result = value * rate / 100
        return {"result": format_number(result), "formula": "Amount × percentage ÷ 100", "steps": [f"{format_number(value)} × {format_number(rate)}% = {format_number(result)}."]}
    if kind == "profit_loss":
        cost = _required(inputs, "cost_price", "cost price")
        selling = _required(inputs, "selling_price", "selling price")
        difference = selling - cost
        label = "Profit" if difference >= 0 else "Loss"
        rate = abs(difference) / cost * 100 if cost else 0
        return {"result": f"{label}: {format_number(abs(difference))}\n{label} percentage: {format_number(rate)}%", "formula": "(Selling price − cost price) ÷ cost price × 100", "steps": [f"Difference = {format_number(selling)} − {format_number(cost)} = {format_number(difference)}."]}
    if kind == "discount":
        price = _required(inputs, "price", "original price")
        rate = _required(inputs, "rate", "discount percentage")
        amount = price * rate / 100
        return {"result": f"Discount: {format_number(amount)}\nFinal price: {format_number(price - amount)}", "formula": "Discount = price × rate ÷ 100", "steps": [f"Subtract the discount {format_number(amount)} from {format_number(price)}."]}
    if kind == "gst":
        price = _required(inputs, "price", "price")
        rate = _required(inputs, "rate", "GST rate")
        tax = price * rate / 100
        return {"result": f"GST: {format_number(tax)}\nTotal including GST: {format_number(price + tax)}", "formula": "GST = price × rate ÷ 100", "steps": [f"Add {format_number(tax)} GST to the pre-tax amount {format_number(price)}."]}
    if kind in {"simple_interest", "compound_interest"}:
        principal = _required(inputs, "principal", "principal")
        rate = _required(inputs, "rate", "annual rate")
        years = _required(inputs, "time", "time in years")
        if years < 0 or principal < 0:
            raise CalculationError("Principal and time cannot be negative.")
        if kind == "simple_interest":
            interest = principal * rate * years / 100
            total = principal + interest
            formula = "Simple interest = principal × rate × time ÷ 100"
        else:
            frequency = _required(inputs, "frequency", "compounding frequency")
            if frequency <= 0:
                raise CalculationError("Compounding frequency must be greater than zero.")
            total = principal * (1 + rate / (100 * frequency)) ** (frequency * years)
            interest = total - principal
            formula = "A = P(1 + r/n)ⁿᵗ"
        return {"result": f"Interest: {format_number(interest)}\nTotal: {format_number(total)}", "formula": formula, "steps": [f"Principal {format_number(principal)} grows by {format_number(interest)} over {format_number(years)} years."]}
    if kind == "emi":
        principal = _required(inputs, "principal", "loan amount")
        annual_rate = _required(inputs, "rate", "annual rate")
        years = _required(inputs, "time", "tenure in years")
        if min(principal, years) < 0:
            raise CalculationError("Loan amount and tenure cannot be negative.")
        months = years * 12
        monthly_rate = annual_rate / 1200
        if months == 0:
            raise CalculationError("Tenure must be greater than zero.")
        emi = principal / months if monthly_rate == 0 else principal * monthly_rate * (1 + monthly_rate) ** months / ((1 + monthly_rate) ** months - 1)
        total = emi * months
        return {"result": f"Monthly EMI: {format_number(emi)}\nTotal payment: {format_number(total)}\nTotal interest: {format_number(total - principal)}", "formula": "EMI = P × r × (1 + r)ⁿ ÷ ((1 + r)ⁿ − 1)", "steps": [f"Monthly rate = {format_number(monthly_rate * 100)}%; number of payments = {format_number(months)}."]}
    raise CalculationError("Choose a supported financial calculation.")


def calculate(calculator_type, inputs, expression="", angle_mode="degrees"):
    calculator_type = str(calculator_type or "").lower()
    if calculator_type == "normal":
        result = evaluate_expression(expression, angle_mode)
        return {"result": format_number(result), "formula": expression, "steps": [f"Evaluate using the standard order of operations: {format_number(result)}."]}
    if calculator_type == "scientific":
        result = evaluate_expression(expression, angle_mode)
        return {"result": format_number(result), "formula": expression, "steps": [f"Evaluate in {angle_mode}: {format_number(result)}."]}
    if calculator_type == "shape":
        return calculate_shape(inputs)
    if calculator_type == "equation":
        kind = str(inputs.get("equation_type", "linear")).lower()
        if kind == "simultaneous":
            return solve_two_variable_equations(str(inputs.get("equation1", "")), str(inputs.get("equation2", "")))
        equation = str(inputs.get("equation", "")).strip()
        if equation:
            return solve_equation(equation)
        # Backward-compatible coefficient inputs.
        a = _required(inputs, "a", "coefficient a")
        b = _required(inputs, "b", "coefficient b")
        c = _required(inputs, "c", "coefficient c") if kind == "quadratic" else 0.0
        return solve_coefficients(a if kind == "quadratic" else 0.0, a if kind == "linear" else b, b if kind == "linear" else c)
    if calculator_type == "unit":
        return convert_unit(inputs)
    if calculator_type == "financial":
        return calculate_financial(inputs)
    raise CalculationError("Choose a supported calculator.")


def solve_basic_word_problem(prompt):
    """Handle a small, explicit set of common queries without using an LLM."""
    if not isinstance(prompt, str):
        return None
    text = prompt.strip()
    if not text or len(text) > 2000:
        return None
    lowered = text.lower().replace(",", "")

    percent_match = re.search(r"(-?\d+(?:\.\d+)?)\s*(?:percent|per cent|%)\s*(?:of)\s*(-?\d+(?:\.\d+)?)", lowered)
    if percent_match:
        rate, value = map(float, percent_match.groups())
        amount = value * rate / 100
        return {
            "answer": format_number(amount),
            "interpreted_problem": f"{format_number(rate)}% of {format_number(value)}",
            "calculation": f"{format_number(value)} × {format_number(rate)} ÷ 100 = {format_number(amount)}",
            "explanation": "Convert the percentage to a fraction by dividing by 100, then multiply by the amount.",
        }

    gst_match = re.search(r"(-?\d+(?:\.\d+)?)\s*%\s*gst\s*(?:on|of)\s*(-?\d+(?:\.\d+)?)", lowered)
    if gst_match:
        rate, price = map(float, gst_match.groups())
        tax = price * rate / 100
        return {
            "answer": f"GST: {format_number(tax)}; total: {format_number(price + tax)}",
            "interpreted_problem": f"Add {format_number(rate)}% GST to {format_number(price)}",
            "calculation": f"Tax = {format_number(price)} × {format_number(rate)}% = {format_number(tax)}",
            "explanation": "Add the calculated GST amount to the original price.",
        }

    circle_match = re.search(r"circle.*?radius\s*(?:of|=|:)?\s*(-?\d+(?:\.\d+)?)", lowered)
    if circle_match and "area" in lowered:
        radius = float(circle_match.group(1))
        if radius < 0:
            raise CalculationError("Radius cannot be negative.")
        area = math.pi * radius * radius
        return {
            "answer": format_number(area),
            "interpreted_problem": f"Area of a circle with radius {format_number(radius)}",
            "calculation": f"π × {format_number(radius)}² = {format_number(area)}",
            "explanation": "A circle's area is π times the radius squared.",
        }

    if "left" in lowered and any(word in lowered for word in ("spend", "spent", "use", "used")):
        amounts = re.findall(r"-?\d+(?:\.\d+)?", lowered)
        if len(amounts) >= 2:
            total, spent = map(float, amounts[:2])
            left = total - spent
            return {
                "answer": format_number(left),
                "interpreted_problem": f"Subtract {format_number(spent)} from {format_number(total)}",
                "calculation": f"{format_number(total)} − {format_number(spent)} = {format_number(left)}",
                "explanation": "Subtract the amount spent from the amount you started with.",
            }

    equation_match = re.search(r"(?:find\s*x\s*if|solve)\s*:?\s*(.+?=\s*[-+.\d]+)", text, re.IGNORECASE)
    equation = equation_match.group(1) if equation_match else None
    if equation:
        solved = solve_equation(equation)
        return {
            "answer": solved["result"],
            "interpreted_problem": equation.strip(),
            "calculation": "\n".join(solved["steps"]),
            "explanation": solved["formula"],
        }
    return None


def category_for(calculator_type):
    value = str(calculator_type or "").strip().lower()
    mapping = {
        "normal": "Basic", "normal calculator": "Basic",
        "scientific": "Scientific", "scientific calculator": "Scientific",
        "shape": "Shape", "shape calculator": "Shape",
        "equation": "Equation", "equation calculator": "Equation",
        "unit": "Unit", "unit converter": "Unit",
        "financial": "Financial", "financial calculator": "Financial",
        "prompt calculator": "AI", "image math solver": "AI",
        "voice calculator": "AI", "ai math solver": "AI",
        "mistake detector": "AI", "explain my answer": "AI",
        "ai math tutor": "AI", "ai": "AI",
        "graph calculator": "Advanced", "graph": "Advanced",
        "what-if comparison": "Advanced", "whatif": "Advanced",
        "multiple solution methods": "Advanced", "quadratic": "Advanced",
        "advanced financial tools": "Advanced", "dashboard": "Advanced",
    }
    return mapping.get(value, "Advanced")
