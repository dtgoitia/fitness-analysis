import datetime
import json
import os
import sys
import webbrowser
from dataclasses import asdict, dataclass
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


Activities = list[Activity]
History = list[CompletedActivity]


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


def extract_data_from_file(path: Path) -> tuple[Activities, History]:
    with path.open("r") as f:
        data: FitnessJsonData = json.load(f)

    raw_activities = data["activities"]
    raw_history = data["completedActivities"]

    activities = list(map(cast_activity, raw_activities))
    history = list(map(cast_completed_activity, raw_history))

    return activities, history


# TODO: add support for CSV files
def find_json_files(dir: Path) -> list[Path]:
    all_json_paths = sorted(
        path
        for path in dir.glob("*.json")
        if path.name.startswith("fitness-tracker__backup_")
    )

    return all_json_paths


class ActivityMismatch(Exception):
    ...


class CompletedActivityMismatch(Exception):
    ...


def js_isodate(d: datetime.datetime) -> str:
    return f"{d.isoformat()}Z"


def save_aggregated_data(activities: Activities, history: History, dir: Path) -> None:
    path = dir / "aggregated_data.json"

    data = {
        "date": js_isodate(datetime.datetime.now()),
        "activities": [asdict(activity) for activity in activities],
        "completedActivities": [
            {
                **asdict(completed_activity),
                "date": js_isodate(completed_activity.date),
            }
            for completed_activity in history
        ],
    }

    with path.open("w") as f:
        json.dump(data, fp=f, indent=2)


def aggregate_data_from_files(paths: list[Path]) -> tuple[Activities, History]:
    activities_by_id: dict[ActivityId, Activity] = {}
    history_by_id: dict[CompletedActivityId, CompletedActivity] = {}
    for path in paths:
        print(path.name)
        file_activities, file_history = extract_data_from_file(path=path)

        # aggregate activities and report collisions
        for activity in file_activities:
            activity_id = activity.id
            if existing_activity := activities_by_id.get(activity_id):
                if existing_activity != activity:
                    raise ActivityMismatch(
                        "Different activities have the same ID:\n"
                        "existing_activity:\n"
                        f"{existing_activity}\n"
                        "\n"
                        "activity:\n"
                        f"{activity}\n"
                    )
                else:
                    continue
            else:
                activities_by_id[activity_id] = activity

        # aggregate completed activities and report collisions
        for completed_activity in file_history:
            completed_activity_id = completed_activity.id
            if existing_completed_activity := history_by_id.get(completed_activity_id):
                if existing_completed_activity != completed_activity:
                    raise CompletedActivityMismatch(
                        "Different completed activities have the same ID:\n"
                        "existing_activity:\n"
                        f"{existing_completed_activity}\n"
                        "\n"
                        "activity:\n"
                        f"{completed_activity}\n"
                    )
                else:
                    continue
            else:
                history_by_id[completed_activity_id] = completed_activity

    activities = sorted(activities_by_id.values(), key=lambda a: a.name)
    history = sorted(history_by_id.values(), key=lambda ca: ca.date)

    save_aggregated_data(activities=activities, history=history, dir=path.parent)

    return activities, history


def read_data(dir: Path) -> tuple[list[ActivityName], list[str], Any]:
    json_files = find_json_files(dir=dir)
    activities, history = aggregate_data_from_files(paths=json_files)

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
    im = ax.imshow(
        harvest,
        cmap="gray",
        vmin="0",
    )

    # Show all ticks and label them with the respective list entries
    ax.set_xticks(np.arange(len(farmers)), labels=farmers)
    ax.set_yticks(np.arange(len(vegetables)), labels=vegetables)

    # Rotate the tick labels and set their alignment.
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

    # Loop over data dimensions and create text annotations.
    for i in range(len(vegetables)):
        for j in range(len(farmers)):
            value = harvest[i, j]
            value_text = f"{value}" if value else "·"
            text = ax.text(j, i, value_text, ha="center", va="center", color="w")

    fig.tight_layout()
    fig.set_size_inches(18, 18)
    fig.savefig(output_path)

    webbrowser.open(f"file://{output_path.absolute()}", new=0)


def main() -> None | str:
    data = read_data(dir=Path(os.environ["FITNESS_DATA_DIR"]))
    _plot(data=data, output_path=Path("chart.png"))
    return None


if __name__ == "__main__":
    sys.exit(main())
