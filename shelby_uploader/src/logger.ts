type LogLevel = "INFO" | "WARN" | "ERROR" | "DEBUG";

export function log(level: LogLevel, msg: string, meta: Record<string, unknown> = {}): void {
  const ts = new Date().toISOString();
  const extras = Object.keys(meta).length ? " " + JSON.stringify(meta) : "";
  console.log(`[${ts}] [${level}] ${msg}${extras}`);
}
