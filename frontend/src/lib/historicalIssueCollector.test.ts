import { describe, expect, it } from "vitest";
import { parseCollectorPayload } from "./historicalIssueCollector";

describe("historical issue collector output", () => {
  it("parses the final JSON line after diagnostic output", () => {
    const payload = parseCollectorPayload(
      [
        '{"event":"progress"}',
        '{"success":true,"data":{"schemaVersion":"historical-issue-analysis-v9"}}',
      ].join("\n"),
    );

    expect(payload?.success).toBe(true);
    expect(payload?.data?.schemaVersion).toBe("historical-issue-analysis-v9");
  });

  it("returns null for malformed output", () => {
    expect(parseCollectorPayload("not-json")).toBeNull();
  });
});
