import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import Customizer from "./Customizer";
import type { Item } from "../types";
const item: Item = {
  id: 1,
  name: "Aloo Burger",
  price: 14000,
  description: "Freshly made",
  category_id: 1,
  image_url: "",
  available: true,
  hidden: false,
  vegetarian: true,
  is_combo: false,
  sort_order: 0,
  groups: [
    {
      id: 1,
      name: "Spice",
      min_select: 1,
      max_select: 1,
      options: [
        { id: 1, name: "Mild", price: 0 },
        { id: 2, name: "Spicy", price: 0 },
      ],
    },
    {
      id: 2,
      name: "Extras",
      min_select: 0,
      max_select: 1,
      options: [{ id: 3, name: "Cheese", price: 2000 }],
    },
  ],
};
describe("item customization", () => {
  it("requires a selection, calculates extras and preserves instructions", async () => {
    const user = userEvent.setup();
    const save = vi.fn();
    render(<Customizer item={item} onSave={save} onClose={() => {}} />);
    await user.click(screen.getByRole("button", { name: /Add to order/ }));
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Choose 1–1 options for Spice",
    );
    expect(save).not.toHaveBeenCalled();
    await user.click(screen.getByLabelText(/Mild/));
    await user.click(screen.getByLabelText(/Cheese/));
    await user.click(screen.getByRole("button", { name: "Increase quantity" }));
    await user.type(screen.getByLabelText("Special instructions"), "Less oil");
    expect(
      screen.getByRole("button", { name: /Add to order/ }),
    ).toHaveTextContent("₹320");
    await user.click(screen.getByRole("button", { name: /Add to order/ }));
    expect(save).toHaveBeenCalledWith(
      expect.objectContaining({
        quantity: 2,
        unit_price: 16000,
        option_ids: [1, 3],
        instructions: "Less oil",
      }),
    );
  });
  it("limits single selection and supports optional clearing", async () => {
    const user = userEvent.setup();
    const save = vi.fn();
    render(<Customizer item={item} onSave={save} onClose={() => {}} />);
    await user.click(screen.getByLabelText(/Mild/));
    await user.click(screen.getByLabelText(/Spicy/));
    await user.click(screen.getByLabelText(/Cheese/));
    await user.click(screen.getByText("Clear selection"));
    await user.click(screen.getByRole("button", { name: /Add to order/ }));
    expect(save).toHaveBeenCalledWith(
      expect.objectContaining({ option_ids: [2], unit_price: 14000 }),
    );
  });
});
