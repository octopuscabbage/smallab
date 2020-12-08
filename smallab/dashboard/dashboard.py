import curses
import logging
import math
import multiprocessing as mp
import time

import scipy.stats as stats
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import OneHotEncoder

from smallab.dashboard.dashboard_events import (BeginEvent, CompleteEvent, ProgressEvent, LogEvent,
                                                StartExperimentEvent, RegistrationCompleteEvent,
                                                RegisterEvent, FailedEvent)

# This is a globally accessible queue which stores the events for the dashboard

encoders = dict()  # feature name : dict("encoder" : OneHotEncoder, "values" : list of values)
specification_ids_to_specification = dict()
keys_with_numeric_vals = []


class TimeEstimator:
    """
    This is used to record how long it takes for one iteration of an experiment and how long it takes to complete an experiment
    It uses this and the number of remaining experiments and iterations to compute the median and lower and upper quartile
    time to complete the entire batch
    """

    def __init__(self):
        self.cur_calls = 0  # resets every batch_size calls to compute_time_stats
        self.batch_size = 10
        self.last_estimate = (0, 0, 0)  # This way we can return the same time estimate every batch_size frames
        self.iteration_dataset = {}  # Maps specifications to list of iteration times
        self.completion_dataset = {}  # Maps specifications to list of completion times
        self.last_update_time = dict()
        self.start_time = dict()
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

        self.iteration_dataset.setdefault(specification, []).append(unit_time_diff)

    def record_completion(self, specification):
        current_time = time.time()
        time_diff = current_time - self.start_time[specification]
        self.completion_dataset.setdefault(specification, []).append(time_diff)
        self.last_update_time[specification] = current_time

    def compute_time_stats(self, specification_progress, active, registered):
        # Calculate this differently it should be remaining_progress + active_not_in_progress
        # Dictionary is empty, use number active and completion time to estimate
        # The math here is a little wonky since idk if median and quartiles work with iterated expectation

        if not (active or self.iteration_dataset):
            return 0, 0, 0
        # elif self.cur_calls < self.batch_size:
        #     self.cur_calls += 1
        #     return self.last_estimate

        # --- Create and fit the models using the iteration dataset ---
        xs, l_ys, m_ys, h_ys = [], [], [], []  # specs, lower, mid, and higher quantiles
        for spec_id, times in self.iteration_dataset.items():
            xs.append(self.spec_id_to_entry(spec_id))
            l_ys.append([np.quantile(times, .25)])
            m_ys.append([np.quantile(times, .50)])
            h_ys.append([np.quantile(times, .75)])
        l_model = LinearRegression().fit(xs, l_ys)
        m_model = LinearRegression().fit(xs, m_ys)
        h_model = LinearRegression().fit(xs, h_ys)

        # --- Predict remaining time for each active specification ---
        running = []
        for spec_id in active:  # Get specs of running experiments
            running.append(self.spec_id_to_entry(spec_id))
        # Get predictions for each running experiment, then loop through them to
        predictions = [m_model.predict(running), l_model.predict(running), h_model.predict(running)]
        self.last_estimate = float("-inf"), 0, 0
        for i, spec_id in enumerate(active):
            remaining_iterations = specification_progress[spec_id][1] - specification_progress[spec_id][0]  # max - cur
            t = predictions[0][i][0] * remaining_iterations
            print(t)
            if t > self.last_estimate[0]:
                self.last_estimate = (t, predictions[1][i][0] * remaining_iterations,
                                      predictions[2][i][0] * remaining_iterations)

        self.cur_calls = 0
        return self.last_estimate

    def spec_id_to_entry(self, spec_id):
        """
        NOTE: Defaults are set to "" (empty str) and 0 for encoded and numerical values, respectively.
              Might cause errors if not taken into account.
        """
        spec, entry = specification_ids_to_specification[spec_id], []

        for key in sorted(encoders.keys()):
            # Unpack encoding into entry
            entry += [v[0] for v in encoders[key]["encoder"].transform([[spec.get(key, "")]]).toarray()]

        for key in keys_with_numeric_vals:
            value = spec.get(key, 0)
            if isinstance(value, bool):
                entry.append(int(value))
            else:
                entry.append(value)

        return entry

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
                       timeestimator, failed, in_slow_mode):
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
    if in_slow_mode:
        completed_failed_string += " !!! You are logging too fast !!!"
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
            status_string = "{progress}/{max_amount} : ".format(progress=round(progress,2), max_amount=round(max_amount,2))
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

        specification = str(specification_id_to_specification[active_specification])
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
            except Exception as e:
                stdscr.addstr(row,0, str(e)[:width])
            row += 1
    return row


def run(stdscr,eventQueue):
    global specification_ids_to_specification
    max_events_per_frame = 100
    max_log_spool_events = 10**3
    timeestimator = TimeEstimator()
    log_spool = []
    active = []
    complete = []
    experiment_name = ""
    specification_progress = dict()
    registered = []
    failed = []
    start_time = time.time()
    specification_readout_index = 0
    while True:
        if time.time() - start_time > 1:
            specification_readout_index += 1
        # Drain Queue:
        try:
            i = 0
            while not eventQueue.empty() and i < max_events_per_frame:
                i += 1
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
                    spec = dict(event.specification)
                    specification_ids_to_specification[event.specification_id] = spec
                    update_possible_values(spec)
                elif isinstance(event, FailedEvent):
                    active.remove(event.specification_id)
                    failed.append(event.specification_id)
                elif isinstance(event, RegistrationCompleteEvent):
                    fit_encoders()
                else:
                    print("Dashboard action not understood")
            in_slow_mode = False
            if i == max_events_per_frame:
                in_slow_mode = True
            # Draw Screen
            stdscr.clear()

            height, width = stdscr.getmaxyx()
            row = 0
            row = draw_header_widget(row, stdscr, experiment_name, width, complete, active, registered,
                                     specification_progress, timeestimator, failed, in_slow_mode=in_slow_mode)
            row = draw_specifications_widget(row, stdscr, active, registered, width, specification_progress, height,
                                             failed, specification_ids_to_specification, specification_readout_index)
            row = draw_log_widget(row, stdscr, width, height, log_spool)
            stdscr.refresh()
            time.sleep(0.1)
            log_spool = log_spool[-max_log_spool_events:]
        except Exception as e:
            logging.getLogger("smallab.dashboard").error("Dashboard Error {}".format(e), exc_info=True)


def update_possible_values(spec: dict):
    # NOTE: keys that have a mix of numeric objects and other objects are not handled
    for key, value in spec.items():
        key_info = encoders.get(key, None)

        # key gets ignored if numeric and already found
        if key_info:
            vals = key_info["values"]
            if value not in vals:
                vals.append([value])
        elif not isinstance(value, (bool, int, float, complex)):
            encoders[key] = {"encoder": OneHotEncoder(), "values": [[value], [""]]}  # handle_unknown='ignore'
        elif key not in keys_with_numeric_vals:
            keys_with_numeric_vals.append(key)


def fit_encoders():
    for key, val in encoders.items():
        encoders[key]["encoder"].fit(encoders[key]["values"])


def start_dashboard(eventQueue):
    curses.wrapper(run,eventQueue)

