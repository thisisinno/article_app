import { describe, expect, it } from "vitest";
import { ApiError } from "../lib/api";
import { isActiveRequest, isRequestCancellation } from "../lib/request-state";

describe("latest request state guards", () => {
  it("treats caller cancellation as silent", () => {
    const controller = new AbortController();
    expect(
      isRequestCancellation(
        new ApiError("The request was cancelled.", 0, "request_aborted"),
        controller.signal,
      ),
    ).toBe(true);
  });

  it("does not let a stale request replace newer data or finish its loading", () => {
    const controller = new AbortController();
    let current = 1;
    let loading = true;
    let data = "";
    const first = current;
    const second = ++current;

    if (isActiveRequest(second, current, controller.signal)) data = "newest";
    if (isActiveRequest(first, current, controller.signal)) data = "stale";
    if (isActiveRequest(first, current, controller.signal)) loading = false;

    expect(data).toBe("newest");
    expect(loading).toBe(true);
  });

  it.each(["network_error", "request_timeout"])(
    "keeps a genuine %s failure visible",
    (code) => {
      const controller = new AbortController();
      const error = new ApiError("Retry this request.", 0, code, true);
      expect(isRequestCancellation(error, controller.signal)).toBe(false);
      expect(isActiveRequest(3, 3, controller.signal)).toBe(true);
    },
  );
});
