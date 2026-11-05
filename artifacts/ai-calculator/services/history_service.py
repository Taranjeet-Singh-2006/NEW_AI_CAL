import calendar
from datetime import date, datetime, time, timedelta

from sqlalchemy import func, or_

from models import CalculationHistory, db
from services.calculator_service import category_for


def serialize_history(record):
    created_at = record.created_at
    timestamp = created_at.isoformat(timespec="seconds") + "Z" if created_at else None
    return {
        "id": record.id,
        "input_expression": record.input_expression,
        "result": record.result,
        "category": record.category,
        "calculator_type": record.calculator_type,
        "purpose": record.purpose,
        "created_at": timestamp,
    }


def save_history(payload):
    expression = str(payload.get("input_expression", "")).strip()
    result = str(payload.get("result", "")).strip()
    calculator_type = str(payload.get("calculator_type", "")).strip()
    if not expression or not result or not calculator_type:
        raise ValueError("A calculation, result, and calculator type are required.")
    if len(expression) > 2000 or len(result) > 4000 or len(calculator_type) > 80:
        raise ValueError("One of the history fields is too long.")
    purpose = str(payload.get("purpose", "")).strip()[:240] or None
    record = CalculationHistory(
        input_expression=expression,
        result=result,
        category=category_for(calculator_type),
        calculator_type=calculator_type,
        purpose=purpose,
    )
    db.session.add(record)
    db.session.commit()
    return serialize_history(record)


def _date_boundaries(period, start_date=None, end_date=None):
    today = date.today()
    if period == "today":
        return datetime.combine(today, time.min), datetime.combine(today + timedelta(days=1), time.min)
    if period == "yesterday":
        yesterday = today - timedelta(days=1)
        return datetime.combine(yesterday, time.min), datetime.combine(today, time.min)
    if period == "week":
        start = today - timedelta(days=today.weekday())
        return datetime.combine(start, time.min), datetime.combine(today + timedelta(days=1), time.min)
    if period == "month":
        start = today.replace(day=1)
        next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        return datetime.combine(start, time.min), datetime.combine(next_month, time.min)
    if period == "custom":
        try:
            start = date.fromisoformat(start_date) if start_date else None
            end = date.fromisoformat(end_date) if end_date else None
        except ValueError:
            raise ValueError("Choose valid custom dates.") from None
        if start and end and start > end:
            raise ValueError("The start date must be on or before the end date.")
        return (
            datetime.combine(start, time.min) if start else None,
            datetime.combine(end + timedelta(days=1), time.min) if end else None,
        )
    return None, None


def list_history(filters):
    query = CalculationHistory.query
    search = str(filters.get("search", "")).strip()[:200]
    if search:
        pattern = f"%{search}%"
        search_fields = [
                CalculationHistory.input_expression.ilike(pattern),
                CalculationHistory.result.ilike(pattern),
                CalculationHistory.category.ilike(pattern),
                CalculationHistory.calculator_type.ilike(pattern),
                CalculationHistory.purpose.ilike(pattern),
        ]
        month_number = next(
            (f"{month:02d}" for month in range(1, 13) if search.casefold() in calendar.month_name[month].casefold()),
            None,
        )
        if month_number:
            search_fields.append(func.strftime("%m", CalculationHistory.created_at) == month_number)
        query = query.filter(or_(*search_fields))
    category = str(filters.get("category", "")).strip()
    if category:
        query = query.filter(CalculationHistory.category == category)
    calculator_type = str(filters.get("calculator_type", "")).strip()[:80]
    if calculator_type:
        query = query.filter(CalculationHistory.calculator_type.ilike(f"%{calculator_type}%"))
    start, end = _date_boundaries(
        str(filters.get("period", "")),
        filters.get("start_date"),
        filters.get("end_date"),
    )
    if start:
        query = query.filter(CalculationHistory.created_at >= start)
    if end:
        query = query.filter(CalculationHistory.created_at < end)
    records = query.order_by(CalculationHistory.created_at.desc(), CalculationHistory.id.desc()).limit(250).all()
    return [serialize_history(record) for record in records]


def delete_history_item(record_id):
    record = db.session.get(CalculationHistory, record_id)
    if record is None:
        return False
    db.session.delete(record)
    db.session.commit()
    return True


def clear_history():
    deleted = db.session.query(CalculationHistory).delete(synchronize_session=False)
    db.session.commit()
    return deleted


def dashboard_summary():
    now = datetime.now()
    today_start = datetime.combine(date.today(), time.min)
    week_start = datetime.combine(date.today() - timedelta(days=date.today().weekday()), time.min)
    total = CalculationHistory.query.count()
    today_count = CalculationHistory.query.filter(CalculationHistory.created_at >= today_start).count()
    week_count = CalculationHistory.query.filter(CalculationHistory.created_at >= week_start).count()
    most_used_row = (
        db.session.query(CalculationHistory.calculator_type, func.count(CalculationHistory.id).label("amount"))
        .group_by(CalculationHistory.calculator_type)
        .order_by(func.count(CalculationHistory.id).desc())
        .first()
    )
    common_category_row = (
        db.session.query(CalculationHistory.category, func.count(CalculationHistory.id).label("amount"))
        .group_by(CalculationHistory.category)
        .order_by(func.count(CalculationHistory.id).desc())
        .first()
    )
    recent = (
        CalculationHistory.query
        .order_by(CalculationHistory.created_at.desc(), CalculationHistory.id.desc())
        .limit(8)
        .all()
    )
    month_start = date(now.year, now.month, 1)
    for _ in range(11):
        month_start = (month_start.replace(day=1) - timedelta(days=1)).replace(day=1)
    monthly_records = CalculationHistory.query.filter(
        CalculationHistory.created_at >= datetime.combine(month_start, time.min)
    ).all()
    month_counts = {}
    for record in monthly_records:
        key = record.created_at.strftime("%Y-%m")
        month_counts[key] = month_counts.get(key, 0) + 1
    months = []
    cursor = month_start
    for _ in range(12):
        key = cursor.strftime("%Y-%m")
        months.append({"month": cursor.strftime("%b %Y"), "count": month_counts.get(key, 0)})
        cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
    return {
        "total_calculations": total,
        "today_calculations": today_count,
        "week_calculations": week_count,
        "most_used_calculator": most_used_row[0] if most_used_row else None,
        "most_common_category": common_category_row[0] if common_category_row else None,
        "monthly_activity": months,
        "recent_activity": [serialize_history(record) for record in recent],
    }
