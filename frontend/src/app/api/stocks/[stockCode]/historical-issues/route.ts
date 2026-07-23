import { execFile } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { promisify } from "node:util";
import type {
  HistoricalIssueApiResponse,
  HistoricalIssueRequestBody,
} from "@/lib/historicalIssues";
import { getStockIssues } from "@/lib/issueRepository";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const execFileAsync = promisify(execFile);

interface CollectorCommand {
  executable: string;
  prefixArgs: string[];
  source: string;
  requiresExistingFile: boolean;
}

class CollectorRuntimeUnavailableError extends Error {
  constructor() {
    super("collector-runtime-unavailable");
    this.name = "CollectorRuntimeUnavailableError";
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

function configuredPythonCommand(value: string): CollectorCommand {
  const hasPathSeparator = value.includes("/") || value.includes("\\");
  return {
    executable: hasPathSeparator && !path.isAbsolute(value)
      ? path.resolve(repositoryRoot(), value)
      : value,
    prefixArgs: [],
    source: "STOCKECHO_PYTHON",
    requiresExistingFile: hasPathSeparator || path.isAbsolute(value),
  };
}

function pythonCandidates(root: string): CollectorCommand[] {
  const configured = process.env.STOCKECHO_PYTHON?.trim();
  const candidates: CollectorCommand[] = [
    ...(configured ? [configuredPythonCommand(configured)] : []),
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
  return typeof value === "string" ? value : Buffer.isBuffer(value)
    ? value.toString("utf8")
    : "";
}

function processErrorCode(error: unknown): string | number | undefined {
  if (!error || typeof error !== "object" || !("code" in error)) return undefined;
  const code = (error as { code?: unknown }).code;
  return typeof code === "string" || typeof code === "number" ? code : undefined;
}

function stderrSummary(error: unknown, root: string): string {
  const stderr = processOutput(error, "stderr")
    .replaceAll(root, "<repository>")
    .trim();
  return stderr.slice(-800);
}

async function resolveCollectorCommand(root: string): Promise<CollectorCommand> {
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
          env: process.env,
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

function parseCollectorPayload(output: string): HistoricalIssueApiResponse | null {
  const lines = output.trim().split("\n").filter(Boolean);
  try {
    return JSON.parse(lines.at(-1) ?? "{}") as HistoricalIssueApiResponse;
  } catch {
    return null;
  }
}

function collectorSetupResponse() {
  return Response.json(
    {
      success: false,
      errorCode: "collector_runtime_unavailable",
      error:
        "Collector Python 환경이 준비되지 않았습니다. 저장소 루트에서 가상환경을 만들고 requirements.txt를 설치해 주세요.",
    } satisfies HistoricalIssueApiResponse,
    { status: 503 },
  );
}

function isRequestBody(value: unknown): value is HistoricalIssueRequestBody {
  if (!value || typeof value !== "object") return false;
  const body = value as Partial<HistoricalIssueRequestBody>;
  return (
    typeof body.topicId === "string"
    && typeof body.eventId === "string"
    && typeof body.eventDate === "string"
    && typeof body.name === "string"
    && typeof body.topicLabel === "string"
    && Array.isArray(body.keywords)
    && body.keywords.every((keyword) => typeof keyword === "string")
  );
}

export async function POST(
  request: Request,
  context: RouteContext<"/api/stocks/[stockCode]/historical-issues">,
) {
  const { stockCode } = await context.params;
  if (!/^\d{6}$/.test(stockCode)) {
    return Response.json(
      {
        success: false,
        error: "올바른 6자리 종목 코드가 필요합니다.",
      } satisfies HistoricalIssueApiResponse,
      { status: 400 },
    );
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return Response.json(
      {
        success: false,
        error: "요청 본문이 올바른 JSON이 아닙니다.",
      } satisfies HistoricalIssueApiResponse,
      { status: 400 },
    );
  }
  if (!isRequestBody(body)) {
    return Response.json(
      {
        success: false,
        error: "현재 Event 정보와 키워드가 필요합니다.",
      } satisfies HistoricalIssueApiResponse,
      { status: 400 },
    );
  }

  let stockIssues;
  try {
    stockIssues = await getStockIssues(stockCode);
  } catch (error) {
    console.error("[historical-issues] Current issue lookup failed.", {
      stockCode,
      errorName: error instanceof Error ? error.name : "unknown",
    });
    return Response.json(
      {
        success: false,
        errorCode: "issue_lookup_failed",
        error: "현재 주요 이슈 데이터를 확인하지 못했습니다.",
      } satisfies HistoricalIssueApiResponse,
      { status: 503 },
    );
  }
  const canonicalIssue = stockIssues?.issues.find(
    (issue) =>
      issue.eventId === body.eventId
      && issue.topicId === body.topicId
      && issue.eventDate === body.eventDate,
  );
  if (!canonicalIssue) {
    return Response.json(
      {
        success: false,
        error: "현재 저장된 주요 이슈와 일치하지 않는 요청입니다.",
      } satisfies HistoricalIssueApiResponse,
      { status: 409 },
    );
  }

  let root: string;
  let command: CollectorCommand;
  try {
    root = repositoryRoot();
    command = await resolveCollectorCommand(root);
  } catch (error) {
    if (error instanceof CollectorRuntimeUnavailableError) {
      console.error("[historical-issues] Collector runtime is unavailable.", {
        stockCode,
      });
      return collectorSetupResponse();
    }
    throw error;
  }
  const args = [
    "-m",
    "collector.jobs.analyze_historical_issue",
    "--stock-code",
    stockCode,
    "--topic-id",
    canonicalIssue.topicId,
    "--event-id",
    canonicalIssue.eventId,
    "--event-date",
    canonicalIssue.eventDate,
    "--name",
    canonicalIssue.name,
    "--topic-label",
    canonicalIssue.topicLabel,
    ...canonicalIssue.keywords.flatMap((keyword) => ["--keyword", keyword]),
  ];

  try {
    const { stdout } = await execFileAsync(
      command.executable,
      [...command.prefixArgs, ...args],
      {
        cwd: root,
        timeout: 120_000,
        maxBuffer: 4 * 1024 * 1024,
        env: process.env,
        windowsHide: true,
      },
    );
    const payload = parseCollectorPayload(stdout);
    if (!payload?.success || !payload.data) {
      throw new Error("historical-analysis-failed");
    }
    return Response.json(payload, {
      headers: { "Cache-Control": "no-store" },
    });
  } catch (error) {
    const payload = parseCollectorPayload(processOutput(error, "stdout"));
    console.error("[historical-issues] Collector execution failed.", {
      stockCode,
      code: processErrorCode(error),
      stderr: stderrSummary(error, root),
      errorCode: payload?.errorCode ?? "analysis_failed",
    });
    if (payload?.errorCode === "collector_configuration_missing") {
      return Response.json(payload, { status: 503 });
    }
    return Response.json(
      {
        success: false,
        errorCode: payload?.errorCode ?? "analysis_failed",
        error: "과거 유사 이슈 분석을 완료하지 못했습니다. 잠시 후 다시 시도해 주세요.",
      } satisfies HistoricalIssueApiResponse,
      { status: 500 },
    );
  }
}
