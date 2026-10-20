# TOSS menu - owner revision, 19 October 2026

The owner-supplied poster dated 2026-10-19 is the current source. The POS contains
27 items across 11 categories. Prices below are rupees; stored prices are paise.
The existing black, magenta, purple and yellow interface is retained.

| Section | Item / portion | Price in rupees |
| --- | --- | --- |
| Crispy Tenders | 2 / 4 / 6 pieces | 149 / 199 / 259 |
| Wings | 2 / 4 / 6 pieces | 139 / 179 / 229 |
| Fried Chicken Drumsticks | 2 / 4 / 6 pieces | 119 / 149 / 219 |
| Burgers | Crispy Chick / Nash Cheese / Steak Bite / Smash Chick / Triple Stack | 169 / 189 / 199 / 199 / 299 |
| Loaded Fries | Chicken Loaded / Nashville Cheese / Paneer Chick Loaded | 169 / 189 / 179 |
| Wraps | Chicken Loaded / Nashville Chicken / Paneer / Mushroom | 129 / 129 / 119 / 109 |
| Mocktails | Tossy Blue / Cool Toss / Pink Venom | 79 each |
| Veg Burgers | Mushroom / Paneer | 109 / 129 |
| Veg Wraps | Paneer / Mushroom | 109 each |
| Veg Fries | Peri Peri / Cheese | 79 / 99 |
| Combo Deals | Toss Bite - Combo 1 / Toss Wings - Combo 2 / Toss Wrap - Combo 3 | 329 / 349 / 379 |

The user confirmed keeping the category-specific Paneer Wrap prices: 119 in Wraps
and 109 in Veg Wraps. Mushroom Wrap is listed in both sections at 109.
Descriptions are brief labels, not ingredient or allergen specifications.

## Modifiers and combos

Portions require one selection. The old 8-piece options are removed.
One sauce is optional and free on tenders, wings, fried chicken drumsticks,
loaded fries, wraps, veg burgers, veg wraps and veg fries. Choose Drizzle, Dry rub
(sauce on the side), or Toss with the sauce; leave both blank for a plain item.
This follows the owner's explicit free-sauce instruction.
Burger extra cheese costs 29 and an extra dip costs 19.

Eight signature sauces: Cajun Mayo, Peri Peri Mayo, Chilli Garlic Mayo, Buffalo
Sauce, Nashville Hot Cheese, Fiery Glaze, Honey Mustard and Garlic Blaze.
Hot Honey Glaze and BBQ Ranch are removed from the current selections.

Each combo includes a required choice of Tossy Blue, Cool Toss or Pink Venom at
no extra charge:

- Toss Bite - Combo 1: Crispy Chick Burger + fries + mocktail.
- Toss Wings - Combo 2: four wings + loaded fries + mocktail.
- Toss Wrap - Combo 3: Chicken Loaded Wrap + peri peri fries + mocktail.

Retired dishes: Double Cheese Burger, Peri Peri Fries under Loaded Fries, and
Paneer Loaded Fries under Veg Fries. Records are archived, not deleted.
The new poster's Paneer Chick Loaded Fries label is retained exactly; its
chicken content was confirmed by the user, so it is marked non-vegetarian.

## Fresh and existing installations

Fresh installations seed this revision automatically. Existing installations
must apply the update explicitly after a database backup:

```sh
# From backend, using that installation's DATABASE_URL:
python -m app.toss_menu --update-existing

# Or for an existing Docker Compose installation:
docker compose exec api python -m app.toss_menu --update-existing
```

The update is transactional. It updates recognized TOSS item names, prices,
descriptions and modifier choices while keeping item IDs, uploaded photos,
availability and visibility settings. Renamed dishes retain their IDs. Custom
dishes remain. Shared TOSS modifier groups are updated globally; any custom item
assigned those same groups also receives the revised choices.

Past order names, quantities, prices and modifier snapshots are unchanged.
Running the explicit update twice does not duplicate items or modifiers. Normal
startup does not reset admin edits; running the importer without the update flag
also preserves existing matching records. Menu clients refresh within 15 seconds.

Backend tests include both fresh seeding and an upgrade from the previous poster,
including old-order preservation, stable IDs and rejection of removed options.

## Local iPad use and assets

See [LOCAL-IPAD.md](LOCAL-IPAD.md) for the local-computer + iPad setup.
Food imagery is decorative AI-generated artwork, not a photograph of the truck's
actual servings. Uploaded product photos take precedence. The logo is rendered
in code; Anton is bundled with its font license.

[Asset files and generation prompts](frontend/public/images/ASSETS.md).
