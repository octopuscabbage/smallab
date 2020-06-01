import curses
import logging
import math
import multiprocessing as mp
import time

import numpy as np

from smallab.dashboard.dashboard_events import (BeginEvent, CompleteEvent, ProgressEvent, LogEvent,
                                                StartExperimentEvent,
                                                RegisterEvent, FailedEvent)

# This is a globally accessible queue which stores the events for the dashboard
eventQueue = mp.Queue(maxsize=200)


class TimeEstimator():
    """
    This is used to record how long it takes for one iteration of an experiment and how long it takes to complete an experiment
    It uses this and the number of remaining experiments and iterations to compute the median and lower and upper quartile
    time to complete the entire batch
    """

    def __init__(self):
        self.last_update_time = dict()
        self.start_time = dict()
        self.time_per_iterations = []
        self.time_per_completion = []
        self.last_progress = dict()

    def record_start(self, specification):
        self.start_time[specification] = time.time()
        self.last_update_time[specification] = time.time()

    def record_iteration(self, specification, progress):
        if specification not in self.last_progress:
            # TODO this will likely be wrong when resuming, it assumes the progress started at 0
            progress_amount = progress
            self.last_progress[specification] = progress
        else:
            progress_amount = progress - self.last_progress[specification]
            self.last_progress[specification] = progress
        current_time = time.time()
        time_diff = current_time - self.last_update_time[specification]
        self.last_update_time[specification] = current_time
        if progress_amount != 0:
            unit_time_diff = time_diff / progress_amount
        else:
            unit_time_diff = time_diff

        self.time_per_iterations.append(unit_time_diff)

    def record_completion(self, specification):
        current_time = time.time()
        time_diff = current_time - self.start_time[specification]
        self.time_per_completion.append(time_diff)
        self.last_update_time[specification] = current_time

    def compute_time_stats(self, specification_progress, active, registered):
        # Calculate this differently it should be remaining_progress + active_not_in_progress
        # Dictionary is empty, use number active and completion time to estimate
        # The math here is a little wonky since idk if median and quartiles work with iterated expectation

        expected_seconds_to_complete_all = 0
        lower_quartile_complete_all = 0
        higher_quartile_complete_all = 0
        if self.time_per_completion:
            times_to_complete = np.array(self.time_per_completion)
            # this finds the number experiments with no progress (so they are not double counted when counting iterations remaining)
            remaining_amount_with_no_progress = len(registered) + len(
                list(filter(lambda x: not x in specification_progress, active)))

            average_seconds_to_complete = np.median(times_to_complete)
            expected_seconds_to_complete_all = average_seconds_to_complete * remaining_amount_with_no_progress
            lower_quartile_complete_all = np.quantile(average_seconds_to_complete,
                                                      .25) * remaining_amount_with_no_progress
            higher_quartile_complete_all = np.quantile(average_seconds_to_complete,
                                                       .75) * remaining_amount_with_no_progress

        if self.time_per_iterations:
            times_per_iteration = np.array(self.time_per_iterations)
            remaining_iterations = sum(
                [max_num - current_progress for current_progress, max_num in specification_progress.values()])
            if not self.time_per_completion:
                remaining_amount_with_no_progress = len(registered) + len(
                    list(filter(lambda x: not x in specification_progress, active)))
                average_max = np.mean([max_num for current_progress, max_num in specification_progress.values()])
                remaining_iterations += average_max * remaining_amount_with_no_progress

            expected_seconds_to_complete_all += np.median(times_per_iteration) * remaining_iterations
            lower_quartile_complete_all += np.quantile(times_per_iteration,
                                                       .25) * remaining_iterations
            higher_quartile_complete_all += np.quantile(times_per_iteration,
                                                        .75) * remaining_iterations

        # Divide by active number since that's the amount of processes running
        if active:
            return expected_seconds_to_complete_all / len(active), lower_quartile_complete_all / len(
                active), higher_quartile_complete_all / len(active)
        else:
            return 0, 0, 0


intervals = (
    ('weeks', 604800),  # 60 * 60 * 24 * 7
    ('days', 86400),  # 60 * 60 * 24
    ('hours', 3600),  # 60 * 60
    ('minutes', 60),
    ('seconds', 1),
)


def display_time(seconds, granularity=2):
    result = []

    for name, count in intervals:
        value = seconds // count
        if value:
            seconds -= value * count
            if value == 1:
                name = name.rstrip('s')
            result.append("{} {}".format(value, name))
    return ', '.join(result[:granularity])


def draw_header_widget(row, stdscr, experiment_name, width, complete, active, registered, specification_progress,
                       timeestimator, failed):
    stdscr.addstr(0, 0, "Smallab Running: {name}".format(name=experiment_name))
    row += 1
    stdscr.addstr(row, 0, "-" * width)
    row += 1
    completed_failed_string = "Completed {num_complete} / {num_total}".format(num_complete=len(complete),
                                                                              num_total=len(complete) + len(
                                                                                  active) + len(
                                                                                  registered))
    if failed:
        completed_failed_string += " - Failed: {num_failed}".format(num_failed=len(failed))
    stdscr.addstr(row, 0, completed_failed_string)
    t = timeestimator.compute_time_stats(specification_progress, active, registered)
    if t is not None:
        expected, lower, higher = t
        completion_stats_string = "Completion - Expected: {expectedstr} - Upper: {upperstr} - Lower: {lowerstr}".format(
            expectedstr=display_time(expected), upperstr=display_time(higher), lowerstr=display_time(lower))
        stdscr.addstr(row, width - len(completion_stats_string), completion_stats_string)
    row += 1
    stdscr.addstr(row, 0, "-" * width)
    row += 1
    return row


def draw_specifications_widget(row, stdscr, active, registered, width, specification_progress, height, failed,
                               specification_id_to_specification, specification_readout_index):
    start_row = row
    # Decide to draw in single or double column
    second_column_begins = math.floor(width / 2)
    max_height = math.floor(height / 2)
    use_double_column_layout = width >= 40 and len(active) + len(registered) > max_height - row
    on_second_column = False
    try:
        max_specification_length = max(map(len, active + registered + failed)) + 1
    except ValueError:
        max_specification_length = 0
    for i, active_specification in enumerate(active + registered + failed):
        if use_double_column_layout and on_second_column:
            stdscr.addstr(row, second_column_begins, active_specification)
            specification_readout_start_index = second_column_begins + max_specification_length
        else:
            stdscr.addstr(row, 0, active_specification)
            specification_readout_start_index = max_specification_length
        if use_double_column_layout:
            bar_width = math.floor(width / 8)
        else:
            bar_width = math.floor(width / 4)

        if active_specification in specification_progress:
            progress, max_amount = specification_progress[active_specification]
            status_string = "{progress}/{max_amount} : ".format(progress=progress, max_amount=max_amount)
            amount_complete = progress / max_amount
            bars_complete = math.floor(amount_complete * bar_width)
            bars_not_complete = bar_width - bars_complete
            status_string += "=" * bars_complete
            status_string += " " * bars_not_complete


        elif active_specification in active:
            status_string = "Running..."
        elif active_specification in failed:
            status_string = "Failed!"
        else:
            status_string = "Waiting..."
        if use_double_column_layout and not on_second_column:
            status_string += "||"
            stdscr.addstr(row, second_column_begins - len(status_string), status_string)
            specification_readout_end_index = second_column_begins - len(status_string)
        else:
            stdscr.addstr(row, width - len(status_string), status_string)
            specification_readout_end_index = width - len(status_string)

        specification = specification_id_to_specification[active_specification]
        specification_string_start_index = specification_readout_index % len(specification)
        max_allowed_length = specification_readout_end_index - specification_readout_start_index - 1
        if len(specification) <= max_allowed_length:
            stdscr.addstr(row, specification_readout_start_index,
                          specification)
        else:
            overflow = specification_string_start_index + max_allowed_length - len(specification) - 1
            if overflow > 0:
                stdscr.addstr(row, specification_readout_start_index,
                              specification[
                              specification_string_start_index:specification_string_start_index + max_allowed_length] + " " + specification[
                                                                                                                              :overflow])

            else:
                stdscr.addstr(row, specification_readout_start_index,
                              specification[
                              specification_string_start_index:specification_string_start_index + max_allowed_length])
        row += 1
        if row >= max_height:
            if use_double_column_layout and not on_second_column:
                on_second_column = True
                row = start_row
            else:
                break
    assert row <= max_height
    return max_height


def draw_log_widget(row, stdscr, width, height, log_spool):
    stdscr.addstr(row, 0, "=" * width)
    row += 1
    stdscr.addstr(row, 0, "Logs")
    row += 1
    stdscr.addstr(row, 0, "=" * width)
    row += 1
    remaining_rows = height - row
    for log in log_spool[-remaining_rows + 1:]:
        message = log[:width]
        if not message.isspace():
            try:
                stdscr.addstr(row, 0, message)
            except:
                pass
            row += 1
    return row


def run(stdscr):
    timeestimator = TimeEstimator()
    i = 0
    log_spool = []
    active = []
    complete = []
    experiment_name = ""
    specification_progress = dict()
    registered = []
    failed = []
    specification_ids_to_specification = dict()
    start_time = time.time()
    specification_readout_index = 0
    while True:
        if time.time() - start_time > 1:
            specification_readout_index += 1
        # Drain Queue:
        try:
            while not eventQueue.empty():
                event = eventQueue.get()
                if isinstance(event, BeginEvent):
                    registered.remove(event.specification_id)
                    active.append(event.specification_id)
                    timeestimator.record_start(event.specification_id)

                elif isinstance(event, CompleteEvent):
                    active.remove(event.specification_id)
                    complete.append(event.specification_id)
                    timeestimator.record_completion(event.specification_id)
                elif isinstance(event, ProgressEvent):
                    specification_progress[event.specification_id] = (event.progress, event.max)
                    timeestimator.record_iteration(event.specification_id, event.progress)
                elif isinstance(event, LogEvent):
                    if not event.message.isspace():
                        log_spool.append(event.message)
                elif isinstance(event, StartExperimentEvent):
                    experiment_name = event.name
                elif isinstance(event, RegisterEvent):
                    registered.append(event.specification_id)
                    specification_ids_to_specification[event.specification_id] = str(dict(event.specification))
                elif isinstance(event, FailedEvent):
                    active.remove(event.specification_id)
                    failed.append(event.specification_id)
                else:
                    print("Dashboard action not understood")

            # Draw Screen
            stdscr.clear()
            height, width = stdscr.getmaxyx()
            row = 0
            row = draw_header_widget(row, stdscr, experiment_name, width, complete, active, registered,
                                     specification_progress, timeestimator, failed)
            row = draw_specifications_widget(row, stdscr, active, registered, width, specification_progress, height,
                                             failed, specification_ids_to_specification, specification_readout_index)
            row = draw_log_widget(row, stdscr, width, height, log_spool)
            stdscr.refresh()
            time.sleep(0.1)
        except Exception as e:
            logging.getLogger("smallab.dashboard").error("Dashboard Error {}".format(e), exc_info=True)


def start_dashboard():
    curses.wrapper(run)
