import { useEffect, useState } from "react";
import {
  Plus,
  Pencil,
  Trash2,
  Upload,
  Search,
  SlidersHorizontal,
} from "lucide-react";
import type { Category, Group, Item, Menu, User } from "../types";
import type { Notify } from "../App";
import { api, money } from "../api";
import Modal from "../components/Modal";

type ItemForm = Omit<Item, "id" | "groups"> & { group_ids: number[] };
type GroupForm = {
  name: string;
  min_select: number;
  max_select: number;
  options: { name: string; price: number }[];
};
type Editor =
  | { kind: "items"; id?: number; value: ItemForm }
  | { kind: "categories"; id?: number; value: Omit<Category, "id"> }
  | { kind: "groups"; id?: number; value: GroupForm }
  | {
      kind: "users";
      value: { username: string; password: string; role: string };
    };
const itemForm = (item: Item): ItemForm => {
  const { id: _id, groups, ...value } = item;
  return { ...value, group_ids: groups.map((g) => g.id) };
};
export default function Admin({
  revision,
  notify,
  onChanged,
}: {
  revision: number;
  notify: Notify;
  onChanged: () => void;
}) {
  const [menu, setMenu] = useState<Menu | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [tab, setTab] = useState("items");
  const [editor, setEditor] = useState<Editor | null>(null);
  const [deleting, setDeleting] = useState<{
    kind: string;
    id: number;
    name: string;
  } | null>(null);
  const [refresh, setRefresh] = useState(0);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [query, setQuery] = useState("");
  useEffect(() => {
    let active = true;
    Promise.all([api<Menu>("/admin/menu"), api<User[]>("/admin/users")])
      .then(([m, u]) => {
        if (active) {
          setMenu(m);
          setUsers(u);
          setError("");
        }
      })
      .catch((e) => {
        if (active) setError((e as Error).message);
      });
    return () => {
      active = false;
    };
  }, [refresh, revision]);
  const changed = () => {
    setRefresh((n) => n + 1);
    onChanged();
  };
  function add() {
    if (tab === "items") {
      if (!menu?.categories.length) {
        notify("Create a category first.", true);
        return;
      }
      setEditor({
        kind: "items",
        value: {
          category_id: menu.categories[0].id,
          name: "",
          description: "",
          price: 0,
          image_url: "",
          available: true,
          hidden: false,
          is_combo: false,
          vegetarian: true,
          sort_order: 0,
          group_ids: [],
        },
      });
    } else if (tab === "categories")
      setEditor({ kind: "categories", value: { name: "", sort_order: 0 } });
    else if (tab === "groups")
      setEditor({
        kind: "groups",
        value: {
          name: "",
          min_select: 0,
          max_select: 1,
          options: [{ name: "", price: 0 }],
        },
      });
    else
      setEditor({
        kind: "users",
        value: { username: "", password: "", role: "cashier" },
      });
  }
  async function save() {
    if (!editor || busy) return;
    setBusy(true);
    setError("");
    const id = "id" in editor ? editor.id : undefined;
    try {
      await api(`/admin/${editor.kind}${id ? `/${id}` : ""}`, {
        method: id ? "PUT" : "POST",
        body: JSON.stringify(editor.value),
      });
      setEditor(null);
      changed();
      notify("Saved successfully");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function toggle(item: Item, key: "available" | "hidden") {
    if (busy) return;
    setBusy(true);
    try {
      await api(`/admin/items/${item.id}`, {
        method: "PUT",
        body: JSON.stringify({ ...itemForm(item), [key]: !item[key] }),
      });
      changed();
      notify("Menu updated across the truck");
    } catch (e) {
      notify((e as Error).message, true);
    } finally {
      setBusy(false);
    }
  }
  function field(name: string, value: unknown) {
    setEditor((old) =>
      old
        ? ({ ...old, value: { ...old.value, [name]: value } } as Editor)
        : null,
    );
  }
  async function image(file?: File) {
    if (!file) return;
    setBusy(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const result = await api<{ url: string }>("/admin/images", {
        method: "POST",
        body: form,
      });
      field("image_url", result.url);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="standard-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">MAKE IT YOURS</span>
          <h1>Behind the menu</h1>
          <p>A fresh menu. A well-prepared team.</p>
        </div>
        <button className="primary" disabled={!menu || busy} onClick={add}>
          <Plus size={18} />
          Add{" "}
          {tab === "items"
            ? "item"
            : tab === "groups"
              ? "modifier group"
              : tab === "categories"
                ? "category"
                : "team member"}
        </button>
      </div>
      <div className="order-toolbar">
        <div className="filter-tabs">
          {[
            ["items", "Menu items"],
            ["categories", "Categories"],
            ["groups", "Modifiers"],
            ["users", "Team"],
          ].map(([key, label]) => (
            <button
              className={tab === key ? "selected" : ""}
              key={key}
              onClick={() => {
                setTab(key);
                setQuery("");
              }}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="search-box compact">
          <Search size={18} />
          <input
            placeholder="Search…"
            aria-label="Search administration"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
      </div>
      {error && !editor && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {!menu ? (
        <div className="empty-state">Loading menu configuration…</div>
      ) : (
        <div className="admin-list">
          {tab === "items" &&
            menu.items
              .filter((i) => i.name.toLowerCase().includes(query.toLowerCase()))
              .map((item) => (
                <article className="admin-row" key={item.id}>
                  <div className="admin-item-symbol">
                    <SlidersHorizontal size={21} />
                  </div>
                  <div className="admin-row-name">
                    <strong>{item.name}</strong>
                    <small>
                      {
                        menu.categories.find((c) => c.id === item.category_id)
                          ?.name
                      }{" "}
                      · {item.is_combo ? "Combo · " : ""}
                      {item.groups.length} modifier groups · Position{" "}
                      {item.sort_order}
                    </small>
                    <p>{item.description}</p>
                  </div>
                  <strong className="admin-price">{money(item.price)}</strong>
                  <div className="admin-controls">
                    <button
                      disabled={busy}
                      className={`pill toggle ${item.available ? "available" : ""}`}
                      onClick={() => toggle(item, "available")}
                    >
                      {item.available ? "Available" : "Sold out"}
                    </button>
                    <button
                      disabled={busy}
                      className="pill toggle"
                      onClick={() => toggle(item, "hidden")}
                    >
                      {item.hidden ? "Hidden" : "Visible"}
                    </button>
                    <button
                      className="icon-button"
                      aria-label={`Edit ${item.name}`}
                      onClick={() => {
                        setError("");
                        setEditor({
                          kind: "items",
                          id: item.id,
                          value: itemForm(item),
                        });
                      }}
                    >
                      <Pencil size={17} />
                    </button>
                    <button
                      className="icon-button"
                      aria-label={`Delete ${item.name}`}
                      onClick={() =>
                        setDeleting({
                          kind: "items",
                          id: item.id,
                          name: item.name,
                        })
                      }
                    >
                      <Trash2 size={17} />
                    </button>
                  </div>
                </article>
              ))}
          {tab === "categories" &&
            menu.categories
              .filter((c) => c.name.toLowerCase().includes(query.toLowerCase()))
              .map((category) => (
                <article className="admin-row" key={category.id}>
                  <div className="admin-row-name">
                    <strong>{category.name}</strong>
                    <small>
                      Position {category.sort_order} ·{" "}
                      {
                        menu.items.filter((i) => i.category_id === category.id)
                          .length
                      }{" "}
                      items
                    </small>
                  </div>
                  <button
                    className="icon-button"
                    aria-label={`Edit ${category.name}`}
                    onClick={() => {
                      setError("");
                      setEditor({
                        kind: "categories",
                        id: category.id,
                        value: {
                          name: category.name,
                          sort_order: category.sort_order,
                        },
                      });
                    }}
                  >
                    <Pencil size={17} />
                  </button>
                  <button
                    className="icon-button"
                    aria-label={`Delete ${category.name}`}
                    onClick={() =>
                      setDeleting({
                        kind: "categories",
                        id: category.id,
                        name: category.name,
                      })
                    }
                  >
                    <Trash2 size={17} />
                  </button>
                </article>
              ))}
          {tab === "groups" &&
            menu.groups
              .filter((g) => g.name.toLowerCase().includes(query.toLowerCase()))
              .map((group) => (
                <article className="admin-row" key={group.id}>
                  <div className="admin-row-name">
                    <strong>{group.name}</strong>
                    <small>
                      {group.min_select ? "Required" : "Optional"} ·{" "}
                      {group.min_select}–{group.max_select} selections
                    </small>
                    <p>
                      {group.options
                        .map(
                          (o) =>
                            `${o.name}${o.price ? ` (+${money(o.price)})` : ""}`,
                        )
                        .join(" · ")}
                    </p>
                  </div>
                  <button
                    className="icon-button"
                    aria-label={`Edit ${group.name}`}
                    onClick={() => {
                      setError("");
                      setEditor({
                        kind: "groups",
                        id: group.id,
                        value: {
                          name: group.name,
                          min_select: group.min_select,
                          max_select: group.max_select,
                          options: group.options.map(({ name, price }) => ({
                            name,
                            price,
                          })),
                        },
                      });
                    }}
                  >
                    <Pencil size={17} />
                  </button>
                  <button
                    className="icon-button"
                    aria-label={`Delete ${group.name}`}
                    onClick={() =>
                      setDeleting({
                        kind: "groups",
                        id: group.id,
                        name: group.name,
                      })
                    }
                  >
                    <Trash2 size={17} />
                  </button>
                </article>
              ))}
          {tab === "users" &&
            users
              .filter((u) =>
                u.username.toLowerCase().includes(query.toLowerCase()),
              )
              .map((u) => (
                <article className="admin-row" key={u.id}>
                  <span className="avatar">{u.username[0].toUpperCase()}</span>
                  <div className="admin-row-name">
                    <strong>{u.username}</strong>
                    <small>
                      {u.role === "cashier" ? "Order taker" : u.role}
                    </small>
                  </div>
                  <span className="pill">
                    {u.role === "admin"
                      ? "Full access"
                      : u.role === "kitchen"
                        ? "Kitchen operations"
                        : "Ordering & tickets"}
                  </span>
                </article>
              ))}
        </div>
      )}
      {editor && (
        <Modal
          title={`${"id" in editor && editor.id ? "Edit" : "Add"} ${editor.kind === "items" ? "menu item" : editor.kind === "groups" ? "modifier group" : editor.kind === "categories" ? "category" : "team member"}`}
          onClose={() => !busy && setEditor(null)}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void save();
            }}
          >
            {"name" in editor.value && (
              <label className="field">
                Name
                <input
                  required
                  maxLength={editor.kind === "items" ? 150 : 100}
                  value={editor.value.name}
                  onChange={(e) => field("name", e.target.value)}
                />
              </label>
            )}
            {editor.kind === "items" && (
              <>
                <label className="field">
                  Description / combo contents
                  <textarea
                    value={editor.value.description}
                    maxLength={2000}
                    onChange={(e) => field("description", e.target.value)}
                  />
                </label>
                <div className="form-grid">
                  <label className="field">
                    Category
                    <select
                      value={editor.value.category_id}
                      onChange={(e) =>
                        field("category_id", Number(e.target.value))
                      }
                    >
                      {menu?.categories.map((c) => (
                        <option value={c.id} key={c.id}>
                          {c.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <Price
                    value={editor.value.price}
                    onChange={(value) => field("price", value)}
                  />
                </div>
                <label className="field">
                  Display position
                  <input
                    type="number"
                    value={editor.value.sort_order}
                    onChange={(e) =>
                      field("sort_order", Number(e.target.value))
                    }
                  />
                </label>
                <div className="check-grid">
                  {[
                    ["available", "Available"],
                    ["hidden", "Temporarily hidden"],
                    ["is_combo", "This is a combo"],
                    ["vegetarian", "Vegetarian base item"],
                  ].map(([key, label]) => (
                    <label key={key}>
                      <input
                        type="checkbox"
                        checked={Boolean(editor.value[key as keyof ItemForm])}
                        onChange={(e) => field(key, e.target.checked)}
                      />
                      {label}
                    </label>
                  ))}
                </div>
                <fieldset className="modifier-group">
                  <legend>Modifier groups</legend>
                  {menu?.groups.map((g) => (
                    <label className="option" key={g.id}>
                      <input
                        type="checkbox"
                        checked={editor.value.group_ids.includes(g.id)}
                        onChange={(e) =>
                          field(
                            "group_ids",
                            e.target.checked
                              ? [...editor.value.group_ids, g.id]
                              : editor.value.group_ids.filter(
                                  (id) => id !== g.id,
                                ),
                          )
                        }
                      />
                      <span>{g.name}</span>
                      <span className="muted">
                        {g.min_select ? "Required" : "Optional"}
                      </span>
                    </label>
                  ))}
                </fieldset>
                <label className="upload-label">
                  <Upload size={18} />
                  {busy ? "Uploading…" : "Upload food image"}
                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    disabled={busy}
                    onChange={(e) => image(e.target.files?.[0])}
                  />
                </label>
                <p className="muted text-xs">JPEG, PNG or WebP · up to 5 MB</p>
                {editor.value.image_url && (
                  <div className="uploaded-image">
                    <img src={editor.value.image_url} alt="Food preview" />
                    <button
                      type="button"
                      onClick={() => field("image_url", "")}
                    >
                      Remove image
                    </button>
                  </div>
                )}
              </>
            )}
            {editor.kind === "categories" && (
              <label className="field">
                Display position
                <input
                  type="number"
                  value={editor.value.sort_order}
                  onChange={(e) => field("sort_order", Number(e.target.value))}
                />
              </label>
            )}
            {editor.kind === "groups" && (
              <>
                <p className="muted">
                  Minimum 1 makes a group required. Maximum 1 uses single
                  selection; a higher maximum allows multiple selections.
                </p>
                <div className="form-grid">
                  <label className="field">
                    Minimum selections
                    <input
                      type="number"
                      min={0}
                      max={30}
                      required
                      value={editor.value.min_select}
                      onChange={(e) =>
                        field("min_select", Number(e.target.value))
                      }
                    />
                  </label>
                  <label className="field">
                    Maximum selections
                    <input
                      type="number"
                      min={1}
                      max={30}
                      required
                      value={editor.value.max_select}
                      onChange={(e) =>
                        field("max_select", Number(e.target.value))
                      }
                    />
                  </label>
                </div>
                <h3>Options</h3>
                {editor.value.options.map((option, index) => (
                  <div className="option-editor" key={index}>
                    <label className="field">
                      Option name
                      <input
                        required
                        maxLength={100}
                        value={option.name}
                        onChange={(e) =>
                          field(
                            "options",
                            editor.value.options.map((o, i) =>
                              i === index ? { ...o, name: e.target.value } : o,
                            ),
                          )
                        }
                      />
                    </label>
                    <Price
                      value={option.price}
                      onChange={(value) =>
                        field(
                          "options",
                          editor.value.options.map((o, i) =>
                            i === index ? { ...o, price: value } : o,
                          ),
                        )
                      }
                    />
                    <button
                      type="button"
                      className="icon-button"
                      aria-label={`Remove option ${index + 1}`}
                      disabled={editor.value.options.length <= 1}
                      onClick={() =>
                        field(
                          "options",
                          editor.value.options.filter((_, i) => i !== index),
                        )
                      }
                    >
                      <Trash2 size={17} />
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  className="secondary"
                  disabled={editor.value.options.length >= 30}
                  onClick={() =>
                    field("options", [
                      ...editor.value.options,
                      { name: "", price: 0 },
                    ])
                  }
                >
                  <Plus size={16} />
                  Add option
                </button>
              </>
            )}
            {editor.kind === "users" && (
              <>
                <label className="field">
                  Username
                  <input
                    required
                    autoComplete="off"
                    maxLength={80}
                    value={editor.value.username}
                    onChange={(e) => field("username", e.target.value)}
                  />
                </label>
                <label className="field">
                  Password
                  <input
                    required
                    type="password"
                    autoComplete="new-password"
                    minLength={12}
                    maxLength={200}
                    value={editor.value.password}
                    onChange={(e) => field("password", e.target.value)}
                  />
                  <small>At least 12 characters</small>
                </label>
                <label className="field">
                  Role
                  <select
                    value={editor.value.role}
                    onChange={(e) => field("role", e.target.value)}
                  >
                    <option value="cashier">Cashier / order taker</option>
                    <option value="kitchen">Kitchen staff</option>
                    <option value="admin">Administrator</option>
                  </select>
                </label>
              </>
            )}
            {error && (
              <p className="error" role="alert">
                {error}
              </p>
            )}
            <div className="modal-footer">
              <button
                type="button"
                disabled={busy}
                className="secondary"
                onClick={() => setEditor(null)}
              >
                Cancel
              </button>
              <button className="primary" disabled={busy}>
                {busy ? "Saving…" : "Save changes"}
              </button>
            </div>
          </form>
        </Modal>
      )}
      {deleting && (
        <Modal
          title={`Delete ${deleting.name}?`}
          onClose={() => !busy && setDeleting(null)}
        >
          <p>
            This will remove it from the active menu. Past orders retain their
            original details.
          </p>
          <div className="modal-footer">
            <button
              className="secondary"
              disabled={busy}
              onClick={() => setDeleting(null)}
            >
              Keep it
            </button>
            <button
              className="danger"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                try {
                  await api(`/admin/${deleting.kind}/${deleting.id}`, {
                    method: "DELETE",
                  });
                  setDeleting(null);
                  changed();
                  notify("Removed from menu");
                } catch (e) {
                  notify((e as Error).message, true);
                } finally {
                  setBusy(false);
                }
              }}
            >
              Delete
            </button>
          </div>
        </Modal>
      )}
    </main>
  );
}
function Price({
  value,
  onChange,
}: {
  value: number;
  onChange: (value: number) => void;
}) {
  const [text, setText] = useState(String(value / 100));
  useEffect(() => {
    setText((current) =>
      Math.round(Number(current) * 100) === value
        ? current
        : String(value / 100),
    );
  }, [value]);
  return (
    <label className="field">
      Price (₹)
      <input
        type="number"
        min={0}
        max={100000}
        step="0.01"
        required
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          if (e.target.value !== "")
            onChange(Math.round(Number(e.target.value) * 100));
        }}
        onBlur={() => {
          if (text !== "") setText(String(value / 100));
        }}
      />
    </label>
  );
}
