from datetime import date, timedelta
from functools import lru_cache

DayAmount = int


@lru_cache
def one_day() -> timedelta:
    return timedelta(days=1)


@lru_cache
def one_week() -> timedelta:
    return timedelta(days=7)


@lru_cache
def today() -> date:
    return date.today()


@lru_cache
def yesterday() -> date:
    return today() - timedelta(days=1)


@lru_cache
def monday_this_week() -> date:
    _today = today()
    return _today - timedelta(days=_today.weekday())


@lru_cache
def sunday_this_week() -> date:
    return monday_this_week() + one_week() - one_day()


@lru_cache
def first_day_of_month(day: date) -> date:
    return date(year=day.year, month=day.month, day=1)


@lru_cache
def first_day_of_next_month(day) -> date:
    month = day.month
    if month == 12:
        year = day.year + 1
        month = 1
    else:
        year = day.year
        month = day.month + 1

    return date(year=year, month=month, day=1)


@lru_cache
def last_day_of_month(day: date) -> date:
    return first_day_of_next_month(day) - one_day()


@lru_cache
def first_day_of_year(day: date) -> date:
    return date(year=day.year, month=1, day=1)


@lru_cache
def last_day_of_year(day: date) -> date:
    return date(year=day.year + 1, month=1, day=1) - one_day()


@lru_cache
def one_month_ago(day: date) -> date:
    return _n_months_ago(n=1)


def _n_months_ago(n: int) -> date:
    this_month = today().month
    if this_month > n:  # no problem
        year = today().year
        month = this_month - n
    else:
        year_diff = n // 12
        month_diff = n % 12

        year = today().year - year_diff
        month = this_month - month_diff

    if month < 1:
        year -= 1
        month += 12

    return date(year=year, month=month, day=today().day)


def _last_n_months(n: int) -> tuple[date, date]:
    return (
        first_day_of_month(_n_months_ago(n - 1)),
        last_day_of_month(today()),
    )


@lru_cache
def one_year_ago(day: date) -> date:
    return date(year=day.year - 1, month=day.month, day=day.day)


class DateRange:
    this_week = (monday_this_week(), sunday_this_week())
    last_week = (monday_this_week() - one_week(), monday_this_week() - one_day())
    this_month = (first_day_of_month(today()), last_day_of_month(today()))
    last_month = (
        first_day_of_month(one_month_ago(today())),
        last_day_of_month(one_month_ago(today())),
    )
    this_year = (first_day_of_year(today()), last_day_of_year(today()))
    last_year = (
        first_day_of_year(one_year_ago(today())),
        last_day_of_year(one_year_ago(today())),
    )
    last_n_months = _last_n_months


# if today = 2023-01-20:
# assert DateRange.this_week == (date(2023, 1, 16), date(2023, 1, 22))
# assert DateRange.last_week == (date(2023, 1, 9), date(2023, 1, 15))
# assert DateRange.this_month == (date(2023, 1, 1), date(2023, 1, 31))
# assert DateRange.last_month == (date(2022, 12, 1), date(2022, 12, 31))
# assert DateRange.this_year == (date(2023, 1, 1), date(2023, 12, 31))
# assert DateRange.last_year == (date(2022, 1, 1), date(2022, 12, 31))
# assert DateRange.last_n_months(2) == (date(2022, 12, 1), date(2023, 1, 31))
