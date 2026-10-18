import {
  Flame,
  Leaf,
  Sparkles,
  Sandwich,
  CupSoda,
  Drumstick,
  Utensils,
} from "lucide-react";
import type { Item } from "../types";

/** Decorative menu illustrations; an admin-uploaded photo always takes priority. */
export default function TossFoodArt({ item }: { item: Item }) {
  const name = item.name.toLowerCase();
  if (item.is_combo)
    return <div className="menu-photo photo-feast" aria-hidden="true" />;
  if (/burger|stack|crispy chick|nash cheese|steak bite|smash chick/.test(name) && !item.vegetarian)
    return <div className="menu-photo photo-burger" aria-hidden="true" />;
  if (/tender|wing|bucket|joint/.test(name))
    return <div className="menu-photo photo-tenders" aria-hidden="true" />;
  if (/wrap/.test(name) && !item.vegetarian)
    return <div className="menu-photo photo-wrap" aria-hidden="true" />;
  if (/fries/.test(name))
    return <div className="menu-photo photo-fries" aria-hidden="true" />;
  const drink = /lagoon|mojito|mocktail|soda|lassi|chai|tossy blue|cool toss|pink venom/.test(name);
  const Icon = drink
    ? CupSoda
    : item.vegetarian
      ? Leaf
      : /wrap/.test(name)
        ? Sandwich
        : /chicken/.test(name)
          ? Drumstick
          : Utensils;
  const word = drink
    ? "SIP. CHILL."
    : /burger/.test(name)
      ? "ALL VEG."
      : /wrap/.test(name)
        ? "WRAP IT."
        : "TOSS IT.";
  return (
    <div
      className={`toss-illustration ${drink ? "drink-illustration" : "veg-illustration"}`}
      aria-hidden="true"
    >
      <span className="art-orbit" />
      <span className="art-orbit orbit-two" />
      <Icon className="art-main-icon" size={80} strokeWidth={1.25} />
      <Sparkles className="art-spark" size={22} />
      <span className="art-label">{word}</span>
      <Flame className="art-flame" size={18} />
    </div>
  );
}
