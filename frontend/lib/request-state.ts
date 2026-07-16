import { ApiError } from "./api";

export function isActiveRequest(
  requestId: number,
  currentRequestId: number,
  signal: AbortSignal,
) {
  return requestId === currentRequestId && !signal.aborted;
}

export function isRequestCancellation(error: unknown, signal: AbortSignal) {
  return (
    signal.aborted ||
    (error instanceof ApiError && error.code === "request_aborted")
  );
}
