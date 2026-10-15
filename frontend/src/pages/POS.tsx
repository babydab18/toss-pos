import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  ArrowUpRight,
  Check,
  ChefHat,
  Plus,
  Search,
  ShoppingBag,
  Trash2,
  Minus,
  X,
  SlidersHorizontal,
  Utensils,
  Coffee,
  Sandwich,
  Soup,
  Flame,
} from "lucide-react";
import type { Draft, Item, Line, Menu, Order, User } from "../types";
import { api, ApiError, money, newKey, readStored, saveStored } from "../api";
import type { Notify } from "../App";
import Customizer from "../components/Customizer";
import Modal from "../components/Modal";
import TossFoodArt from "../components/TossFoodArt";

export const freshDraft = (): Draft => ({
  items: [],
  customer: "",
  instructions: "",
  submissionKey: newKey(),
  pending: false,
  reason: "",
});
export const draftKey = (id: number) => `streetside-draft-${id}`;
const categoryIcons = [Flame, Utensils, Sandwich, Coffee, Soup];
export default function POS({
  menu,
  user,
  notify,
  online,
  onSubmitted,
}: {
  menu: Menu;
  user: User;
  notify: Notify;
  online: boolean;
  onSubmitted: () => void;
}) {
  const [draft, setDraft] = useState<Draft>(() =>
    readStored(draftKey(user.id), freshDraft()),
  );
  const [category, setCategory] = useState<number | null>(null);
  const [query, setQuery] = useState("");
  const [customizing, setCustomizing] = useState<{
    item: Item;
    line?: Line;
  } | null>(null);
  const [drawer, setDrawer] = useState(false);
  const [clear, setClear] = useState(false);
  const [busy, setBusy] = useState(false);
  const [confirmed, setConfirmed] = useState<Order | null>(null);
  const saving = useRef(false);
  const [storageError, setStorageError] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  useEffect(() => {
    setStorageError(!saveStored(draftKey(user.id), draft));
  }, [draft, user.id]);
  useEffect(() => {
    const editing = (location.state as { editOrder?: Order } | null)?.editOrder;
    if (!editing) return;
    setDraft({
      ...freshDraft(),
      customer: editing.customer,
      instructions: editing.instructions,
      editing: {
        id: editing.id,
        version: editing.version,
        number: editing.number,
      },
      items: editing.items.map((i) => ({
        key: newKey(),
        menu_item_id: i.menu_item_id,
        name: i.name,
        quantity: i.quantity,
        option_ids: i.modifiers.map((m) => m.option_id),
        modifiers: i.modifiers.map((m) => m.name),
        unit_price: i.unit_price,
        instructions: i.instructions,
      })),
    });
    navigate("/", { replace: true, state: null });
    setDrawer(true);
  }, [location.state, navigate]);
  const locked = draft.pending || busy;
  function change(update: Partial<Draft>) {
    if (!locked)
      setDraft((old) => ({ ...old, ...update, submissionKey: newKey() }));
  }
  function saveLine(line: Line) {
    change({
      items: draft.items.some((l) => l.key === line.key)
        ? draft.items.map((l) => (l.key === line.key ? line : l))
        : [...draft.items, line],
    });
    setCustomizing(null);
    notify("Item added to your order");
  }
  function add(item: Item) {
    if (locked) {
      setDrawer(true);
      notify(
        "Resolve the pending submission before changing this order.",
        true,
      );
      return;
    }
    if (item.groups.length) setCustomizing({ item });
    else
      saveLine({
        key: newKey(),
        menu_item_id: item.id,
        name: item.name,
        quantity: 1,
        option_ids: [],
        modifiers: [],
        unit_price: item.price,
        instructions: "",
      });
  }
  const total = draft.items.reduce(
    (sum, line) => sum + line.unit_price * line.quantity,
    0,
  );
  const count = draft.items.reduce((sum, line) => sum + line.quantity, 0);
  const items = menu.items.filter(
    (i) =>
      (category === null || category === i.category_id) &&
      `${i.name} ${i.description}`.toLowerCase().includes(query.toLowerCase()),
  );
  async function send() {
    if (saving.current || !draft.items.length) return;
    saving.current = true;
    setBusy(true);
    const pending = { ...draft, pending: true };
    setDraft(pending);
    if (!saveStored(draftKey(user.id), pending)) {
      setStorageError(true);
      saving.current = false;
      setBusy(false);
      setDraft((d) => ({ ...d, pending: false }));
      notify(
        "Browser storage is unavailable. Enable site storage before sending an order.",
        true,
      );
      return;
    }
    try {
      const body = {
        customer: draft.customer,
        instructions: draft.instructions,
        items: draft.items.map(
          ({ menu_item_id, quantity, option_ids, instructions }) => ({
            menu_item_id,
            quantity,
            option_ids,
            instructions,
          }),
        ),
      };
      const result = await api<Order>(
        draft.editing ? `/orders/${draft.editing.id}` : "/orders",
        {
          method: draft.editing ? "PUT" : "POST",
          headers: { "Idempotency-Key": draft.submissionKey },
          body: JSON.stringify(
            draft.editing
              ? {
                  ...body,
                  version: draft.editing.version,
                  reason: draft.reason,
                }
              : body,
          ),
        },
      );
      setConfirmed(result);
      setDraft(freshDraft());
      setDrawer(false);
      onSubmitted();
    } catch (error) {
      const err = error as ApiError;
      // Unknown delivery outcome keeps the identical payload and key locked for safe retry.
      if (
        err.status >= 400 &&
        err.status < 500 &&
        ![401, 403].includes(err.status)
      )
        setDraft((d) => ({ ...d, pending: false }));
      notify(err.message, true);
    } finally {
      saving.current = false;
      setBusy(false);
    }
  }
  const cart = (
    <>
      <div className="cart-heading">
        <div>
          <span className="eyebrow">
            {draft.editing ? "ORDER CORRECTION" : "CURRENT ORDER"}
          </span>
          <h2>
            {draft.editing ? `Ticket #${draft.editing.number}` : "Your order"}{" "}
            <span className="count-badge">{count}</span>
          </h2>
        </div>
        <button
          className="icon-button mobile-only"
          onClick={() => setDrawer(false)}
          aria-label="Close order"
        >
          <X />
        </button>
      </div>
      <div className="cart-body">
        {storageError && (
          <p className="error">
            Draft storage unavailable. Keep this tab open.
          </p>
        )}
        {draft.pending && (
          <div className="pending-note">
            Confirmation pending. Retry sends the same order safely.{" "}
            {draft.editing &&
              "For corrections, check the Orders screen before retrying."}
          </div>
        )}
        <label className="field customer-field">
          Customer / pickup name
          <input
            placeholder="Add a name (optional)"
            value={draft.customer}
            disabled={locked}
            onChange={(e) => change({ customer: e.target.value })}
            maxLength={100}
          />
        </label>
        {!draft.items.length ? (
          <div className="empty-cart">
            <ShoppingBag size={42} strokeWidth={1.3} />
            <h3>Ready to get tossy?</h3>
            <p>
              Tap something delicious
              <br />
              to get started.
            </p>
          </div>
        ) : (
          <div className="cart-lines">
            {draft.items.map((line) => (
              <article className="cart-line" key={line.key}>
                <div className="flex justify-between gap-3">
                  <button
                    className="line-name"
                    disabled={locked}
                    onClick={() => {
                      const item = menu.items.find(
                        (i) => i.id === line.menu_item_id,
                      );
                      if (item) setCustomizing({ item, line });
                      else
                        notify(
                          "Item no longer on the menu. Remove it to continue.",
                          true,
                        );
                    }}
                  >
                    {line.name}
                    <SlidersHorizontal size={12} />
                  </button>
                  <strong>{money(line.unit_price * line.quantity)}</strong>
                </div>
                {line.modifiers.length > 0 && (
                  <p className="line-detail">{line.modifiers.join(" · ")}</p>
                )}
                {line.instructions && (
                  <p className="line-note">“{line.instructions}”</p>
                )}
                <div className="line-bottom">
                  <div className="quantity">
                    <button
                      disabled={locked || line.quantity === 1}
                      aria-label={`Decrease ${line.name}`}
                      onClick={() =>
                        change({
                          items: draft.items.map((l) =>
                            l.key === line.key
                              ? { ...l, quantity: l.quantity - 1 }
                              : l,
                          ),
                        })
                      }
                    >
                      <Minus size={14} />
                    </button>
                    <span>{line.quantity}</span>
                    <button
                      disabled={locked || line.quantity === 99}
                      aria-label={`Increase ${line.name}`}
                      onClick={() =>
                        change({
                          items: draft.items.map((l) =>
                            l.key === line.key
                              ? { ...l, quantity: l.quantity + 1 }
                              : l,
                          ),
                        })
                      }
                    >
                      <Plus size={14} />
                    </button>
                  </div>
                  <button
                    className="icon-button"
                    disabled={locked}
                    aria-label={`Remove ${line.name}`}
                    onClick={() =>
                      change({
                        items: draft.items.filter((l) => l.key !== line.key),
                      })
                    }
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
        {draft.items.length > 0 && (
          <>
            <label className="field">
              Order note
              <textarea
                rows={2}
                placeholder="Anything the kitchen should know?"
                maxLength={1000}
                value={draft.instructions}
                disabled={locked}
                onChange={(e) => change({ instructions: e.target.value })}
              />
            </label>
            {draft.editing && (
              <label className="field">
                Reason for correction
                <input
                  required
                  maxLength={500}
                  disabled={locked}
                  value={draft.reason}
                  onChange={(e) => change({ reason: e.target.value })}
                  placeholder="Required · e.g. customer changed their order"
                />
              </label>
            )}
          </>
        )}
      </div>
      <div className="cart-footer">
        <div className="subtotal">
          <span>Subtotal</span>
          <span>{money(total)}</span>
        </div>
        <div className="total">
          <span>Estimated total</span>
          <strong>{money(total)}</strong>
        </div>
        <p className="price-caption">
          Based on menu prices and selected extras
        </p>
        <button
          className="primary send-button"
          disabled={
            busy ||
            !count ||
            !online ||
            !!(draft.editing && !draft.reason.trim())
          }
          onClick={send}
        >
          <ChefHat size={20} />
          {busy
            ? "Waiting for kitchen confirmation…"
            : draft.pending
              ? "Retry confirmation"
              : draft.editing
                ? "Send correction"
                : "Send to Kitchen"}
          <ArrowUpRight size={20} />
        </button>
        {count > 0 && (
          <button
            className="clear-button"
            disabled={locked}
            onClick={() => setClear(true)}
          >
            {draft.editing ? "Discard correction" : "Clear order"}
          </button>
        )}
        <div className="cart-footnote">
          <span className="green-dot" />
          Fresh made daily. Full-on flavour.
        </div>
      </div>
    </>
  );
  return (
    <div className="pos-layout">
      <main className="menu-pane">
        <section className="toss-hero" aria-label="TOSS originals">
          <div className="hero-copy">
            <span className="eyebrow">GET CAUGHT IN THE FLAVOUR</span>
            <h1 aria-label="Crispy. Juicy. Drippy.">
              <span>CRISPY. JUICY.</span>
              <span>DRIPPY.</span>
            </h1>
            <p>Fresh made daily. Zero boring bites.</p>
          </div>
          <div className="hero-quality">
            <strong>100%</strong>
            <small>PREMIUM</small>
            <small>QUALITY</small>
          </div>
          <span className="hero-caption">DRENCH. MESSY. ADDICTIVE.</span>
        </section>
        <div className="search-box">
          <Search size={21} />
          <input
            aria-label="Search menu"
            placeholder="Find a dish, drink or a little craving…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          {query && (
            <button onClick={() => setQuery("")} aria-label="Clear search">
              <X size={18} />
            </button>
          )}
        </div>
        <div className="category-tabs">
          <button
            className={category === null ? "selected" : ""}
            onClick={() => setCategory(null)}
          >
            <Utensils size={20} />
            All items<span>{menu.items.length}</span>
          </button>
          {menu.categories.map((cat, i) => {
            const Icon = categoryIcons[i % categoryIcons.length];
            return (
              <button
                key={cat.id}
                className={`${category === cat.id ? "selected" : ""} ${cat.name.startsWith("Veg") ? "veg-category" : ""}`}
                onClick={() => setCategory(cat.id)}
              >
                <Icon size={20} />
                {cat.name}
              </button>
            );
          })}
        </div>
        <div className="menu-section-heading">
          <h2>
            {category === null
              ? "The TOSS lineup"
              : menu.categories.find((c) => c.id === category)?.name}
          </h2>
          <span>{items.length} menu favourites</span>
        </div>
        <div className="menu-grid">
          {items.map((item, index) => (
            <button
              className={`food-card ${!item.available ? "sold-out" : ""}`}
              key={item.id}
              disabled={!item.available}
              onClick={() => add(item)}
              aria-label={`Add ${item.name}`}
            >
              <div className={`food-visual food-tone-${index % 5}`}>
                {item.image_url ? (
                  <img src={item.image_url} alt="" loading="lazy" />
                ) : (
                  <TossFoodArt item={item} />
                )}
                <span
                  className={`diet-mark ${item.vegetarian ? "veg" : "nonveg"}`}
                  title={
                    item.vegetarian ? "Vegetarian base item" : "Non-vegetarian"
                  }
                >
                  ●
                </span>
                {item.is_combo && <span className="combo-tag">COMBO DEAL</span>}
                {!item.available && (
                  <span className="sold-label">Sold out</span>
                )}
              </div>
              <div className="food-card-body">
                <h3>{item.name}</h3>
                <p>{item.description}</p>
                <div className="food-card-bottom">
                  <strong>{money(item.price)}</strong>
                  <span>
                    {item.groups.length ? "Customise" : "Add item"}
                    <Plus size={17} />
                  </span>
                </div>
              </div>
            </button>
          ))}
        </div>
        {!items.length && (
          <div className="empty-state">
            <Search size={32} />
            <h2>No dishes found</h2>
            <p>Try another search or category.</p>
          </div>
        )}
        <p className="menu-bottom-note">
          <strong>WARNING: EXTREME TOSSY FOOD!</strong><span>Menu imagery is illustrative. Your uploaded food photos take priority.</span>
        </p>
      </main>
      <aside className={`cart-pane ${drawer ? "drawer-open" : ""}`}>
        {cart}
      </aside>
      {drawer && (
        <button
          className="drawer-backdrop"
          aria-label="Close order drawer"
          onClick={() => setDrawer(false)}
        />
      )}
      <button className="mobile-cart primary" onClick={() => setDrawer(true)}>
        <ShoppingBag size={20} />
        View order · {count} items<strong>{money(total)}</strong>
      </button>
      {customizing && (
        <Customizer
          {...customizing}
          onSave={saveLine}
          onClose={() => setCustomizing(null)}
        />
      )}
      {clear && (
        <Modal title="Clear this order?" onClose={() => setClear(false)}>
          <p>All items and notes in this draft will be removed.</p>
          <div className="modal-footer">
            <button className="secondary" onClick={() => setClear(false)}>
              Keep order
            </button>
            <button
              className="danger"
              onClick={() => {
                setDraft(freshDraft());
                setClear(false);
              }}
            >
              Clear order
            </button>
          </div>
        </Modal>
      )}
      {confirmed && (
        <Modal
          title={
            confirmed.version > 1
              ? "Correction confirmed"
              : "The kitchen has your order"
          }
          onClose={() => setConfirmed(null)}
        >
          <div className="confirmation">
            <span className="confirmation-check">
              <Check size={30} />
            </span>
            <span className="eyebrow">TICKET NUMBER</span>
            <h1>#{String(confirmed.number).padStart(3, "0")}</h1>
            <p>
              {confirmed.customer || "Walk-in order"} · {money(confirmed.total)}
            </p>
            <p className="muted">Confirmed by the server and saved.</p>
          </div>
          <div className="modal-footer">
            <button
              className="secondary"
              onClick={() => {
                setConfirmed(null);
                navigate("/orders");
              }}
            >
              Track order
            </button>
            <button className="primary" onClick={() => setConfirmed(null)}>
              Next order
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}
