import time
import threading


class Scheduler:

    def __init__(self):
        self.jobs = []

    def add_job(self, func, interval):

        job = {
            "func": func,
            "interval": interval,
            "last_run": 0
        }

        self.jobs.append(job)

    def run(self):

        print("Scheduler started")

        while True:

            now = time.time()

            for job in self.jobs:

                if now - job["last_run"] >= job["interval"]:

                    try:
                        job["func"]()
                    except Exception as e:
                        print(f"Scheduler error: {e}")

                    job["last_run"] = now

            time.sleep(1)