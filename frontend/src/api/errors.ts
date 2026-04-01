export const API_UNREACHABLE = "ERR_API_UNREACHABLE";

export function isApiUnreachable(error: unknown): boolean {
  return error instanceof Error && error.message === API_UNREACHABLE;
}
