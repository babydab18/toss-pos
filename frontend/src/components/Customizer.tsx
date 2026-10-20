import { useState } from "react";
import { Plus, Minus } from "lucide-react";
import type { Item, Line } from "../types";
import { money, newKey } from "../api";
import Modal from "./Modal";

export function selectionError(item: Item, selected: number[]) {
  for (const group of item.groups) {
    const count = group.options.filter((o) => selected.includes(o.id)).length;
    if (count < group.min_select || count > group.max_select)
      return `Choose ${group.min_select}–${group.max_select} options for ${group.name}`;
  }
  const sauce = item.groups.find((g) => g.name === "Free sauce");
  const style = item.groups.find((g) => g.name === "Sauce preparation");
  if (sauce && style && sauce.options.some((o) => selected.includes(o.id)) !== style.options.some((o) => selected.includes(o.id)))
    return "Choose both a free sauce and its preparation, or leave both blank for plain.";
  return "";
}
export default function Customizer({
  item,
  line,
  onSave,
  onClose,
}: {
  item: Item;
  line?: Line;
  onSave: (line: Line) => void;
  onClose: () => void;
}) {
  const [selected, setSelected] = useState<number[]>(line?.option_ids ?? []);
  const [quantity, setQuantity] = useState(line?.quantity ?? 1);
  const [instructions, setInstructions] = useState(line?.instructions ?? "");
  const [error, setError] = useState("");
  const options = item.groups
    .flatMap((g) => g.options)
    .filter((o) => selected.includes(o.id));
  const unitPrice = item.price + options.reduce((sum, o) => sum + o.price, 0);
  function submit() {
    const message = selectionError(item, selected);
    if (message) {
      setError(message);
      return;
    }
    onSave({
      key: line?.key ?? newKey(),
      menu_item_id: item.id,
      name: item.name,
      quantity,
      option_ids: options.map((o) => o.id),
      modifiers: options.map((o) => o.name),
      unit_price: unitPrice,
      instructions,
    });
  }
  return (
    <Modal title={item.name} onClose={onClose}>
      <p className="muted mb-5">{item.description}</p>
      {item.groups.map((group) => (
        <fieldset key={group.id} className="modifier-group">
          <legend>
            {group.name}{" "}
            <span className="pill">
              {group.min_select ? "Required" : "Optional"} ·{" "}
              {group.max_select === 1
                ? "Choose 1"
                : `Up to ${group.max_select}`}
            </span>
          </legend>
          {group.options.map((option) => (
            <label className="option" key={option.id}>
              <input
                type={group.max_select === 1 ? "radio" : "checkbox"}
                name={`group-${group.id}`}
                checked={selected.includes(option.id)}
                onChange={() => {
                  setError("");
                  setSelected((old) =>
                    old.includes(option.id)
                      ? old.filter((id) => id !== option.id)
                      : group.max_select === 1
                        ? [
                            ...old.filter(
                              (id) => !group.options.some((o) => o.id === id),
                            ),
                            option.id,
                          ]
                        : [...old, option.id],
                  );
                }}
              />
              <span>{option.name}</span>
              <span className="muted">
                {option.price ? `+${money(option.price)}` : "No extra cost"}
              </span>
            </label>
          ))}
          {group.min_select === 0 && group.max_select === 1 && (
            <button
              className="text-button"
              onClick={() =>
                setSelected((old) =>
                  old.filter((id) => !group.options.some((o) => o.id === id)),
                )
              }
            >
              Clear selection
            </button>
          )}
        </fieldset>
      ))}
      <label className="field">
        Special instructions
        <textarea
          value={instructions}
          onChange={(e) => setInstructions(e.target.value)}
          maxLength={500}
          placeholder="Less oil, no coriander…"
        />
      </label>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <footer className="modal-footer">
        <div className="quantity">
          <button
            aria-label="Decrease quantity"
            disabled={quantity === 1}
            onClick={() => setQuantity((q) => q - 1)}
          >
            <Minus size={16} />
          </button>
          <strong>{quantity}</strong>
          <button
            aria-label="Increase quantity"
            disabled={quantity === 99}
            onClick={() => setQuantity((q) => q + 1)}
          >
            <Plus size={16} />
          </button>
        </div>
        <button className="primary" onClick={submit}>
          {line ? "Update item" : "Add to order"} ·{" "}
          {money(unitPrice * quantity)}
        </button>
      </footer>
    </Modal>
  );
}
