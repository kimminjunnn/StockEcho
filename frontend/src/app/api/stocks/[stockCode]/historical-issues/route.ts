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

function repositoryRoot(): string {
  const current = process.cwd();
  return existsSync(path.join(current, "collector"))
    ? current
    : path.resolve(current, "..");
}

function pythonExecutable(root: string): string {
  const candidates = [
    process.env.STOCKECHO_PYTHON,
    path.join(root, ".venv", "bin", "python"),
    path.join(root, "venv", "bin", "python"),
    "python3",
  ].filter((value): value is string => Boolean(value));
  return candidates.find((value) => value === "python3" || existsSync(value))
    ?? "python3";
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

  const stockIssues = await getStockIssues(stockCode);
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

  const root = repositoryRoot();
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
    const { stdout } = await execFileAsync(pythonExecutable(root), args, {
      cwd: root,
      timeout: 120_000,
      maxBuffer: 4 * 1024 * 1024,
      env: process.env,
    });
    const lines = stdout.trim().split("\n").filter(Boolean);
    const payload = JSON.parse(
      lines.at(-1) ?? "{}",
    ) as HistoricalIssueApiResponse;
    if (!payload.success || !payload.data) {
      throw new Error("historical-analysis-failed");
    }
    return Response.json(payload, {
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    console.error(`Historical issue analysis failed for ${stockCode}.`);
    return Response.json(
      {
        success: false,
        error: "과거 유사 이슈 분석을 완료하지 못했습니다. 잠시 후 다시 시도해 주세요.",
      } satisfies HistoricalIssueApiResponse,
      { status: 500 },
    );
  }
}
