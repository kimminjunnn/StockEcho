import { execFile } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { promisify } from "node:util";
import type { HistoricalIssueApiResponse } from "@/lib/historicalIssues";
import type { StockIssue } from "@/lib/issues";

const execFileAsync = promisify(execFile);
const ANALYSIS_TIMEOUT_MS = 170_000;

interface CollectorCommand {
  executable: string;
  prefixArgs: string[];
  source: string;
  requiresExistingFile: boolean;
}

export class CollectorRuntimeUnavailableError extends Error {
  constructor() {
    super("collector-runtime-unavailable");
    this.name = "CollectorRuntimeUnavailableError";
  }
}

export class CollectorExecutionError extends Error {
  readonly errorCode: string;
  readonly timedOut: boolean;

  constructor(errorCode: string, timedOut: boolean) {
    super(errorCode);
    this.name = "CollectorExecutionError";
    this.errorCode = errorCode;
    this.timedOut = timedOut;
  }
}

let cachedCollectorCommand:
  | { repositoryRoot: string; command: CollectorCommand }
  | undefined;

function repositoryRoot(): string {
  const configured = process.env.STOCKECHO_REPOSITORY_ROOT?.trim();
  const startingPoints = [
    configured ? path.resolve(configured) : null,
    process.cwd(),
    path.resolve(process.cwd(), ".."),
  ].filter((value): value is string => Boolean(value));

  for (const startingPoint of startingPoints) {
    let candidate = startingPoint;
    for (let depth = 0; depth < 5; depth += 1) {
      if (
        existsSync(path.join(candidate, "collector"))
        && existsSync(path.join(candidate, "requirements.txt"))
      ) {
        return candidate;
      }
      const parent = path.dirname(candidate);
      if (parent === candidate) break;
      candidate = parent;
    }
  }
  throw new CollectorRuntimeUnavailableError();
}

function configuredPythonCommand(
  value: string,
  root: string,
): CollectorCommand {
  const hasPathSeparator = value.includes("/") || value.includes("\\");
  return {
    executable: hasPathSeparator && !path.isAbsolute(value)
      ? path.resolve(root, value)
      : value,
    prefixArgs: [],
    source: "STOCKECHO_PYTHON",
    requiresExistingFile: hasPathSeparator || path.isAbsolute(value),
  };
}

function pythonCandidates(root: string): CollectorCommand[] {
  const configured = process.env.STOCKECHO_PYTHON?.trim();
  const candidates: CollectorCommand[] = [
    ...(configured ? [configuredPythonCommand(configured, root)] : []),
    ...[
      path.join(root, ".venv", "bin", "python"),
      path.join(root, "venv", "bin", "python"),
      path.join(root, ".venv", "Scripts", "python.exe"),
      path.join(root, "venv", "Scripts", "python.exe"),
    ].map((executable) => ({
      executable,
      prefixArgs: [],
      source: "repository-venv",
      requiresExistingFile: true,
    })),
    ...(process.platform === "win32"
      ? [
          {
            executable: "py",
            prefixArgs: ["-3"],
            source: "system-path",
            requiresExistingFile: false,
          },
          {
            executable: "python",
            prefixArgs: [],
            source: "system-path",
            requiresExistingFile: false,
          },
        ]
      : [
          {
            executable: "python3",
            prefixArgs: [],
            source: "system-path",
            requiresExistingFile: false,
          },
          {
            executable: "python",
            prefixArgs: [],
            source: "system-path",
            requiresExistingFile: false,
          },
        ]),
  ];
  const seen = new Set<string>();
  return candidates.filter((candidate) => {
    const key = `${candidate.executable}\u0000${candidate.prefixArgs.join("\u0000")}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function processOutput(error: unknown, key: "stdout" | "stderr"): string {
  if (!error || typeof error !== "object" || !(key in error)) return "";
  const value = (error as Record<string, unknown>)[key];
  return typeof value === "string"
    ? value
    : Buffer.isBuffer(value)
      ? value.toString("utf8")
      : "";
}

function processErrorCode(error: unknown): string | number | undefined {
  if (!error || typeof error !== "object" || !("code" in error)) {
    return undefined;
  }
  const code = (error as { code?: unknown }).code;
  return typeof code === "string" || typeof code === "number"
    ? code
    : undefined;
}

function processTimedOut(error: unknown): boolean {
  if (!error || typeof error !== "object") return false;
  const details = error as { killed?: unknown; signal?: unknown };
  return details.killed === true || details.signal === "SIGTERM";
}

function stderrSummary(error: unknown, root: string): string {
  return processOutput(error, "stderr")
    .replaceAll(root, "<repository>")
    .trim()
    .slice(-800);
}

function collectorEnvironment(): NodeJS.ProcessEnv {
  return {
    ...process.env,
    PYTHONIOENCODING: "utf-8",
    PYTHONUTF8: "1",
  };
}

async function resolveCollectorCommand(
  root: string,
): Promise<CollectorCommand> {
  if (cachedCollectorCommand?.repositoryRoot === root) {
    return cachedCollectorCommand.command;
  }
  for (const candidate of pythonCandidates(root)) {
    if (candidate.requiresExistingFile && !existsSync(candidate.executable)) {
      continue;
    }
    try {
      await execFileAsync(
        candidate.executable,
        [
          ...candidate.prefixArgs,
          "-c",
          "import collector.jobs.analyze_historical_issue",
        ],
        {
          cwd: root,
          timeout: 10_000,
          maxBuffer: 1024 * 1024,
          env: collectorEnvironment(),
          windowsHide: true,
        },
      );
      cachedCollectorCommand = { repositoryRoot: root, command: candidate };
      return candidate;
    } catch (error) {
      console.warn("[historical-issues] Collector Python candidate rejected.", {
        source: candidate.source,
        code: processErrorCode(error),
        stderr: stderrSummary(error, root),
      });
      if (candidate.source === "STOCKECHO_PYTHON") break;
    }
  }
  throw new CollectorRuntimeUnavailableError();
}

export function parseCollectorPayload(
  output: string,
): HistoricalIssueApiResponse | null {
  const lines = output.trim().split("\n").filter(Boolean);
  try {
    return JSON.parse(lines.at(-1) ?? "{}") as HistoricalIssueApiResponse;
  } catch {
    return null;
  }
}

export async function runHistoricalIssueAnalysis(
  stockCode: string,
  issue: StockIssue,
): Promise<HistoricalIssueApiResponse> {
  const root = repositoryRoot();
  const command = await resolveCollectorCommand(root);
  const args = [
    "-m",
    "collector.jobs.analyze_historical_issue",
    "--stock-code",
    stockCode,
    "--topic-id",
    issue.topicId,
    "--event-id",
    issue.eventId,
    "--event-date",
    issue.eventDate,
    "--name",
    issue.name,
    "--topic-label",
    issue.topicLabel,
    ...issue.keywords.flatMap((keyword) => ["--keyword", keyword]),
    ...(issue.category ? ["--category", issue.category] : []),
    "--impact",
    issue.impact ?? "unknown",
  ];

  try {
    const { stdout } = await execFileAsync(
      command.executable,
      [...command.prefixArgs, ...args],
      {
        cwd: root,
        timeout: ANALYSIS_TIMEOUT_MS,
        maxBuffer: 4 * 1024 * 1024,
        env: collectorEnvironment(),
        windowsHide: true,
      },
    );
    const payload = parseCollectorPayload(stdout);
    if (!payload?.success || !payload.data) {
      throw new CollectorExecutionError(
        payload?.errorCode ?? "analysis_failed",
        false,
      );
    }
    return payload;
  } catch (error) {
    if (error instanceof CollectorExecutionError) throw error;
    const payload = parseCollectorPayload(processOutput(error, "stdout"));
    const timedOut = processTimedOut(error);
    console.error("[historical-issues] Collector execution failed.", {
      stockCode,
      code: processErrorCode(error),
      stderr: stderrSummary(error, root),
      errorCode: payload?.errorCode ?? (timedOut ? "analysis_timed_out" : "analysis_failed"),
    });
    throw new CollectorExecutionError(
      payload?.errorCode ?? (timedOut ? "analysis_timed_out" : "analysis_failed"),
      timedOut,
    );
  }
}
