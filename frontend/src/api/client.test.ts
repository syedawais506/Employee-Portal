import axios from "axios";
import { describe, expect, it } from "vitest";

import { extractApiErrorMessage } from "@/api/client";

describe("extractApiErrorMessage", () => {
  it("extracts the message from a well-formed API error envelope", () => {
    const error = new axios.AxiosError("Request failed");
    error.response = {
      data: { error: { code: "PERMISSION_DENIED", message: "You do not have permission.", details: null } },
      status: 403,
      statusText: "Forbidden",
      headers: {},
      config: error.config!,
    };
    expect(extractApiErrorMessage(error)).toBe("You do not have permission.");
  });

  it("falls back to the default message for non-API errors", () => {
    expect(extractApiErrorMessage(new Error("boom"), "Fallback message")).toBe("Fallback message");
  });

  it("falls back to the default message when the error body has no envelope", () => {
    const error = new axios.AxiosError("Request failed");
    error.response = { data: {}, status: 500, statusText: "Error", headers: {}, config: error.config! };
    expect(extractApiErrorMessage(error, "Something went wrong.")).toBe("Something went wrong.");
  });
});
