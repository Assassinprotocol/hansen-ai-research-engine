import datetime


class SystemLogger:

    def __init__(self):
        pass

    def _timestamp(self):
        return datetime.datetime.utcnow().isoformat()

    def info(self, message, mode="strict"):
        print(f"[INFO] {self._timestamp()} | {mode} | {message}")

    def warn(self, message, mode="strict"):
        print(f"[WARN] {self._timestamp()} | {mode} | {message}")

    def error(self, message, mode="strict"):
        print(f"[ERROR] {self._timestamp()} | {mode} | {message}")

    def log_execution(self, provider, intent, prompt_length, status, execution_time_ms):

        print(
            f"[EXECUTION] {self._timestamp()} | "
            f"{provider} | {intent} | "
            f"len={prompt_length} | "
            f"status={status} | "
            f"{execution_time_ms:.2f}ms"
        )