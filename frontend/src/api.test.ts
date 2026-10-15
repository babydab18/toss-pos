import { afterEach, describe, expect, it, vi } from "vitest";
import { api, money, readStored, saveStored } from "./api";
afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});
describe("reliable client boundaries", () => {
  it("never treats a network failure as confirmed", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
    await expect(api("/orders", { method: "POST" })).rejects.toMatchObject({
      status: 0,
    });
  });
  it("reports backend validation messages", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify({ detail: "Item unavailable" }), {
            status: 409,
          }),
        ),
    );
    await expect(api("/orders")).rejects.toThrow("Item unavailable");
  });
  it("preserves drafts and handles corrupt storage", () => {
    saveStored("draft", { items: [1], submissionKey: "same-key" });
    expect(readStored("draft", null)).toEqual({
      items: [1],
      submissionKey: "same-key",
    });
    localStorage.setItem("draft", "bad");
    expect(readStored("draft", { items: [] })).toEqual({ items: [] });
  });
  it("formats integer paise without losing sub-rupee amounts", () => {
    expect(money(14000)).toBe("₹140");
    expect(money(14050)).toBe("₹140.50");
  });
});
