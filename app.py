
import calendar
import re
from datetime import date, timedelta

import streamlit as st


# ==========================================
# 1. 기본 설정
# ==========================================

st.set_page_config(
    page_title="대체공휴일 생성기",
    page_icon="📅",
    layout="wide",
)

st.title("📅 대체공휴일 생성기")
st.caption("연도를 직접 입력하는 공휴일 달력")

WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"]

FIXED_HOLIDAYS = {
    (1, 1): "신정",
    (3, 1): "삼일절",
    (5, 1): "노동절",
    (5, 5): "어린이날",
    (6, 6): "현충일",
    (7, 17): "제헌절",
    (8, 15): "광복절",
    (10, 3): "개천절",
    (10, 9): "한글날",
    (12, 25): "성탄절",
}

ELIGIBLE_FIXED = {
    "삼일절",
    "노동절",
    "어린이날",
    "제헌절",
    "광복절",
    "개천절",
    "한글날",
    "성탄절",
}

EXCLUDED_HOLIDAYS = {"신정", "현충일"}

LUNAR_HOLIDAY_NAMES = {
    "설날연휴",
    "설날",
    "추석연휴",
    "추석",
    "부처님오신날",
}


# ==========================================
# 2. 공휴일 등록
# ==========================================

def add_holiday(holidays, day, name):
    if day not in holidays:
        holidays[day] = []

    if name not in holidays[day]:
        holidays[day].append(name)


def build_fixed_holidays(year):
    holidays = {}

    for (month, day_number), name in FIXED_HOLIDAYS.items():
        try:
            add_holiday(
                holidays,
                date(year, month, day_number),
                name,
            )
        except ValueError:
            pass

    return holidays


# ==========================================
# 3. 음력 공휴일 입력 처리
# ==========================================

def parse_lunar_holidays(text, year, selected_month):
    holidays = {}
    lunar_groups = []
    errors = []

    for line_number, raw_line in enumerate(
        text.splitlines(),
        start=1,
    ):
        line = raw_line.strip()

        if not line:
            continue

        match = re.fullmatch(
            r"(\d{1,2})(?:/(\d{1,2}))?\s+(.+)",
            line,
        )

        if not match:
            errors.append(
                f"{line_number}번째 줄: 날짜와 공휴일 이름을 확인해 줘."
            )
            continue

        first_number = int(match.group(1))
        second_number = match.group(2)
        name = match.group(3).strip()

        if second_number:
            month = first_number
            day_number = int(second_number)
        else:
            month = selected_month
            day_number = first_number

        try:
            start_date = date(year, month, day_number)
        except ValueError:
            errors.append(
                f"{line_number}번째 줄: 날짜가 올바르지 않아."
            )
            continue

        if name in {"설날연휴", "추석연휴"}:
            if name == "설날연휴":
                kind = "설날"
                labels = ["설날연휴", "설날", "설날연휴"]
            else:
                kind = "추석"
                labels = ["추석연휴", "추석", "추석연휴"]

            group_dates = [
                start_date + timedelta(days=i)
                for i in range(3)
            ]

            for holiday_date, label in zip(
                group_dates,
                labels,
            ):
                add_holiday(holidays, holiday_date, label)

            lunar_groups.append({
                "kind": kind,
                "start": start_date,
                "dates": group_dates,
            })

        elif name in LUNAR_HOLIDAY_NAMES:
            add_holiday(holidays, start_date, name)

            if name in {"설날", "추석"}:
                lunar_groups.append({
                    "kind": name,
                    "start": start_date,
                    "dates": [start_date],
                })

        else:
            errors.append(
                f"{line_number}번째 줄: 지원하지 않는 공휴일 이름이야."
            )

    return holidays, lunar_groups, errors


# ==========================================
# 4. 날짜 확인
# ==========================================

def is_weekend(day):
    return day.weekday() >= 5


def is_sunday(day):
    return day.weekday() == 6


def lunar_kind_for_date(day, lunar_groups):
    for group in lunar_groups:
        if day in group["dates"]:
            return group["kind"]

    return None


def next_available_weekday(day, holidays, substitutes):
    candidate = day + timedelta(days=1)

    while (
        is_weekend(candidate)
        or candidate in holidays
        or candidate in substitutes
    ):
        candidate += timedelta(days=1)

    return candidate


# ==========================================
# 5. 대체공휴일 계산
# ==========================================

def generate_substitutes(holidays, lunar_groups):
    substitutes = {}

    original_holidays = {
        day: names[:]
        for day, names in holidays.items()
    }

    for holiday_date in sorted(original_holidays):
        names = original_holidays[holiday_date]

        eligible_names = [
            name for name in names
            if name not in EXCLUDED_HOLIDAYS
        ]

        if not eligible_names:
            continue

        lunar_kind = lunar_kind_for_date(
            holiday_date,
            lunar_groups,
        )

        # 날짜별로 실제 적용 가능한 공휴일 이름을 확인한다.
        eligible_weekend_names = []

        for name in eligible_names:
            if name in ELIGIBLE_FIXED:
                eligible_weekend_names.append(name)

            elif name == "부처님오신날":
                eligible_weekend_names.append(name)

            elif name in {"설날연휴", "설날", "추석연휴", "추석"}:
                if is_sunday(holiday_date):
                    eligible_weekend_names.append(name)

        has_overlap = len(eligible_names) > 1

        if not is_weekend(holiday_date):
            # 평일에 공휴일이 중복되면 한 개만 생성
            count = 1 if has_overlap else 0
        else:
            # 토요일이나 일요일에 대상 공휴일이 중복되면
            # 해당 날짜의 적용 대상 공휴일 수만큼 생성
            count = len(eligible_weekend_names)

        for _ in range(count):
            candidate = next_available_weekday(
                holiday_date,
                original_holidays,
                substitutes,
            )

            substitutes[candidate] = "대체공휴일"

    return substitutes


# ==========================================
# 6. 연도와 월 직접 입력
# ==========================================

today = date.today()

year_column, month_column = st.columns(2)

with year_column:
    year_text = st.text_input(
        "년도 입력",
        value=str(today.year),
        placeholder="예: 2055",
    )

with month_column:
    selected_month = st.selectbox(
        "월",
        list(range(1, 13)),
        index=today.month - 1,
    )

try:
    if not re.fullmatch(r"\d{1,4}", year_text.strip()):
        raise ValueError

    selected_year = int(year_text.strip())

    if not 1 <= selected_year <= 9999:
        raise ValueError

    year_is_valid = True

except ValueError:
    selected_year = today.year
    year_is_valid = False
    st.error("연도는 1부터 9999 사이의 숫자로 입력해 줘.")


# ==========================================
# 7. 음력 공휴일 입력
# ==========================================

st.subheader("음력 공휴일 날짜 입력")

lunar_input = st.text_area(
    "공휴일 입력",
    placeholder=(
        "3 추석연휴\n"
        "16 설날연휴\n"
        "24 부처님오신날\n"
        "4/30 부처님오신날"
    ),
    height=130,
    key="lunar_input",
)

st.caption(
    "월을 생략하면 선택한 월로 처리해. "
    "다른 월은 4/30처럼 월/일로 입력해 줘."
)


# ==========================================
# 8. 대체휴일생성 버튼
# ==========================================

if st.button(
    "대체휴일생성",
    type="primary",
    use_container_width=True,
    disabled=not year_is_valid,
):
    holidays = build_fixed_holidays(selected_year)

    lunar_holidays, lunar_groups, errors = parse_lunar_holidays(
        lunar_input,
        selected_year,
        selected_month,
    )

    for holiday_date, names in lunar_holidays.items():
        for name in names:
            add_holiday(holidays, holiday_date, name)

    substitutes = generate_substitutes(
        holidays,
        lunar_groups,
    )

    st.session_state["holiday_result"] = {
        "year": selected_year,
        "month": selected_month,
        "holidays": holidays,
        "substitutes": substitutes,
        "errors": errors,
    }


# ==========================================
# 9. 달력 표시
# ==========================================

result = st.session_state.get("holiday_result")

if not year_is_valid:
    st.info("올바른 연도를 입력해 줘.")

elif result is None:
    st.info("날짜를 입력한 뒤 「대체휴일생성」 버튼을 눌러 줘.")

elif (
    result["year"] != selected_year
    or result["month"] != selected_month
):
    st.info(
        "연도나 월을 바꿨어. "
        "「대체휴일생성」 버튼을 다시 눌러 줘."
    )

else:
    holidays = result["holidays"]
    substitutes = result["substitutes"]

    for error in result["errors"]:
        st.warning(error)

    st.divider()
    st.subheader(f"{selected_year}년 {selected_month}월")

    st.markdown(
        """
        <style>
        .calendar-day {
            min-height: 105px;
            border: 1px solid #d8d8d8;
            border-radius: 8px;
            padding: 7px;
            margin-bottom: 5px;
            overflow-wrap: anywhere;
        }
        .calendar-number {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .calendar-holiday {
            font-size: 12px;
            line-height: 1.55;
            font-weight: 600;
        }
        .calendar-substitute {
            color: #e67e22;
            font-size: 12px;
            line-height: 1.55;
            font-weight: 700;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # 요일 제목
    header_columns = st.columns(7)

    for index, weekday in enumerate(WEEKDAYS):
        with header_columns[index]:
            if index == 0:
                st.markdown("**:red[일요일]**")
            elif index == 6:
                st.markdown("**:blue[토요일]**")
            else:
                st.markdown(f"**{weekday}요일**")

    # 일요일부터 시작하는 달력
    month_calendar = calendar.Calendar(
        firstweekday=6
    ).monthdatescalendar(
        selected_year,
        selected_month,
    )

    for week in month_calendar:
        columns = st.columns(7)

        for index, day in enumerate(week):
            with columns[index]:
                in_selected_month = day.month == selected_month

                names = holidays.get(day, [])
                substitute_name = substitutes.get(day)

                if substitute_name:
                    number_color = "#e67e22"
                elif names or day.weekday() == 6:
                    number_color = "#e53935"
                elif day.weekday() == 5:
                    number_color = "#1976d2"
                else:
                    number_color = "#333333"

                opacity = "1" if in_selected_month else "0.35"

                holiday_html = ""

                if in_selected_month:
                    for name in names:
                        holiday_html += (
                            '<div class="calendar-holiday" '
                            'style="color:#e53935;">'
                            f'{name}'
                            '</div>'
                        )

                    if substitute_name:
                        holiday_html += (
                            '<div class="calendar-substitute">'
                            '대체공휴일'
                            '</div>'
                        )

                day_html = f"""
                <div class="calendar-day" style="opacity:{opacity};">
                    <div class="calendar-number"
                         style="color:{number_color};">
                        {day.day}
                    </div>
                    {holiday_html}
                </div>
                """

                st.markdown(
                    day_html,
                    unsafe_allow_html=True,
                )

    # ======================================
    # 10. 해당 월 대체공휴일 목록
    # ======================================

    st.divider()
    st.subheader("📌 이번 달 대체공휴일")

    monthly_substitutes = sorted(
        day
        for day in substitutes
        if day.year == selected_year
        and day.month == selected_month
    )

    if monthly_substitutes:
        for day in monthly_substitutes:
            weekday_name = WEEKDAYS[
                (day.weekday() + 1) % 7
            ]

            st.write(
                f"🟠 {day.month}월 {day.day}일 "
                f"({weekday_name}요일) - 대체공휴일"
            )
    else:
        st.write("이번 달에는 계산된 대체공휴일이 없어.")

    st.caption(
        "음력 공휴일은 입력한 날짜를 기준으로 표시해. "
        "임시공휴일 등 별도 지정 날짜는 자동으로 포함되지 않아."
    )
