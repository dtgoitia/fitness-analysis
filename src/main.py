import datetime
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict

import matplotlib.pyplot as plt
import numpy as np

ONE_DAY = datetime.timedelta(days=1)

ActivityId = str
ActivityName = str
CompletedActivityId = str


@dataclass
class DataPoint:
    date: datetime.date


class RawActivity(TypedDict):
    id: str
    name: str
    otherNames: list[str]


class RawCompletedActivity(TypedDict):
    id: str
    activityId: str
    intensity: str
    duration: str
    date: str
    notes: str


class FitnessJsonData(TypedDict):
    date: str
    activities: list
    completedActivities: list[RawCompletedActivity]


@dataclass(frozen=True)
class Activity:
    id: ActivityId
    name: ActivityName
    other_names: list[ActivityName]


@dataclass(frozen=True)
class CompletedActivity:
    id: CompletedActivityId
    activity_id: ActivityId
    intensity: str
    duration: str
    date: datetime.datetime
    notes: str


def cast_activity(raw: RawActivity) -> Activity:
    return Activity(id=raw["id"], name=raw["name"], other_names=raw["otherNames"])


def cast_completed_activity(raw: RawCompletedActivity) -> CompletedActivity:
    return CompletedActivity(
        id=raw["id"],
        activity_id=raw["activityId"],
        intensity=raw["intensity"],
        duration=raw["duration"],
        date=datetime.datetime.fromisoformat(raw["date"].replace("Z", "")),
        notes=raw["notes"],
    )


def compute_dates(history: list[CompletedActivity]) -> list[datetime.date]:
    assert history

    # Find min and max date in history
    min_date = datetime.date.today()
    max_date = datetime.date(2000, 1, 1)
    for activity in history:
        date = activity.date.date()
        min_date = min(min_date, date)
        max_date = max(max_date, date)

    dates: list[datetime.date] = [min_date]
    while True:
        next_day = dates[-1] + ONE_DAY
        dates.append(next_day)
        if next_day == max_date:
            break

    return dates


def compute_data_grid(
    history: list[CompletedActivity],
    dates: list[datetime.date],
    activities: list[ActivityId],
) -> list[list[int]]:

    # Identify how many times each activity occurs on each date
    history_per_activity: dict[ActivityId, dict[datetime.date, int]] = {}
    """
    {
        'act_fnpejwhyrf': { 2022-11-16: 1},
        'act_ibizgrtgva': { 2022-11-16: 1},
        'act_iycrhajvsn': { 2022-11-15: 1,
                            2022-11-16: 1},
        'act_sleeqgovcl': { 2022-11-15: 2},
    }
    """
    for activity in history:
        date = activity.date.date()
        activity_id = activity.activity_id
        if activity_id in history_per_activity:
            if date in history_per_activity[activity_id]:
                history_per_activity[activity_id][date] += 1
            else:
                history_per_activity[activity_id][date] = 1
        else:
            history_per_activity[activity_id] = {date: 1}

    # Build grid and fill up data holes where needed
    data = []
    """
    [
        [1, 1],  # act_fnpejwhyrf
        [2, 0],  # act_ibizgrtgva
        [0, 1],  # act_iycrhajvsn
        [0, 1],  # act_sleeqgovcl
    ]
    """
    for activity_id in activities:
        activity_dates = history_per_activity.get(activity_id, dict())
        day_data = [activity_dates.get(date, 0) for date in dates]
        data.append(day_data)

    return data


def extract_data_from_file(
    path: Path,
) -> tuple[list[Activity], list[CompletedActivity]]:

    with path.open("r") as f:
        data: FitnessJsonData = json.load(f)

    raw_activities = data["activities"]
    raw_history = data["completedActivities"]

    activities = list(map(cast_activity, raw_activities))
    history = list(map(cast_completed_activity, raw_history))

    return activities, history


def read_data(dir: Path) -> tuple[list[ActivityName], list[str], Any]:
    path = dir / "fitness-tracker__backup_20221221-071322.json"  # TODO
    activities, history = extract_data_from_file(path=path)

    activity_index = {activity.id: activity.name for activity in activities}

    # Y-axis labels
    activity_ids: list[ActivityId] = []
    activity_names: list[ActivityName] = []
    for _id, name in activity_index.items():
        activity_ids.append(_id)
        activity_names.append(name)

    # X-axis labels
    dates = compute_dates(history=history)
    formatted_dates = [d.strftime("%-d-%b") for d in dates]

    # Grid data
    data = compute_data_grid(history=history, dates=dates, activities=activity_ids)

    assert len({len(row) for row in data}) == 1, (
        "Every row in `data` must have the same length, but found these different row"
        f" lengths: {[len(row) for row in data]}"
    )
    assert len(activity_names) == len(data), (
        "Activity label amount must match the amount rows in the data, but"
        f" {len(activity_names)} activities found and {len(data)} rows in data"
    )
    assert len(formatted_dates) == len(data[0]), (
        "Date label amount must match the amount of data points per rows in the data"
        f", but {len(formatted_dates)} dates found and {len(data[0])} data points per row in data"
    )

    data_array = np.array(data)

    return activity_names, formatted_dates, data_array


def _plot(data: Any, output_path: Path) -> None:
    (vegetables, farmers, harvest) = data

    fig, ax = plt.subplots()
    im = ax.imshow(harvest)

    # Show all ticks and label them with the respective list entries
    ax.set_xticks(np.arange(len(farmers)), labels=farmers)
    ax.set_yticks(np.arange(len(vegetables)), labels=vegetables)

    # Rotate the tick labels and set their alignment.
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

    # Loop over data dimensions and create text annotations.
    for i in range(len(vegetables)):
        for j in range(len(farmers)):
            text = ax.text(j, i, harvest[i, j], ha="center", va="center", color="w")

    fig.tight_layout()
    fig.set_size_inches(10.5, 18.5)
    fig.savefig(output_path)


def main() -> None | str:
    data = read_data(dir=Path(os.environ["FITNESS_DATA_DIR"]))
    _plot(data=data, output_path=Path("chart.png"))
    return None


if __name__ == "__main__":
    sys.exit(main())