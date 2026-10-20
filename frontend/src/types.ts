export type Role = "admin" | "cashier" | "kitchen";
export type User = { id: number; username: string; role: Role };
export type Option = { id: number; name: string; price: number };
export type Group = {
  id: number;
  name: string;
  min_select: number;
  max_select: number;
  options: Option[];
};
export type Category = { id: number; name: string; sort_order: number };
export type Item = {
  id: number;
  category_id: number;
  name: string;
  description: string;
  price: number;
  image_url: string;
  available: boolean;
  hidden: boolean;
  is_combo: boolean;
  vegetarian: boolean;
  sort_order: number;
  groups: Group[];
};
export type Menu = { categories: Category[]; items: Item[]; groups: Group[] };
export type Line = {
  key: string;
  menu_item_id: number;
  name: string;
  quantity: number;
  option_ids: number[];
  modifiers: string[];
  unit_price: number;
  instructions: string;
};
export type Draft = {
  items: Line[];
  customer: string;
  phone: string;
  sms_opt_in: boolean;
  instructions: string;
  submissionKey: string;
  pending: boolean;
  editing?: { id: string; version: number; number: number };
  reason: string;
};
export type Status = "new" | "preparing" | "ready" | "completed" | "cancelled";
export type Order = {
  id: string;
  number: number;
  day: string;
  created_at: string;
  ready_at: string | null;
  sms_status: string;
  status: Status;
  customer: string;
  phone: string;
  sms_opt_in: boolean;
  instructions: string;
  total: number;
  version: number;
  items: {
    id: number;
    menu_item_id: number;
    name: string;
    base_price: number;
    unit_price: number;
    quantity: number;
    instructions: string;
    modifiers: {
      option_id: number;
      group_name: string;
      name: string;
      price: number;
    }[];
  }[];
  history: { at: string; status: Status; reason: string; changes: unknown }[];
};
