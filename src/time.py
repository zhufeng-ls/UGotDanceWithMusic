import time
from datetime import datetime
import numpy as np


class Time:
    def __init__(self):
        self.time_points = []

    def add_time_point(self):
        current_time = time.time()
        # print(format(current_time))
        self.time_points.append(current_time)

    def print(self):
        if len(self.time_points) < 2:
            print("Not enough time points recorded.")
            return

        start_time = self.time_points[0]
        end_time = self.time_points[-1]
        print("Start Time:", self.format_time(start_time))
        print("End Time:", self.format_time(end_time))

        # original_array = np.array(self.time_points)
        # diff = np.diff(original_array)
        self.time_points = []

        return end_time - start_time

    @staticmethod
    def now():
        current_time = time.time()
        return Time.format_time(current_time)

    @staticmethod
    def format_time(timestamp):
        dt = datetime.fromtimestamp(timestamp)
        formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S.%f")
        return formatted_time

