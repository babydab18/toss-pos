# TOSS menu and visual reference

The supplied TOSS poster is the source for the menu and brand direction: black, magenta, purple, yellow, condensed uppercase lettering and dramatic food imagery. Dark mode is now the default; the light variant remains available.

The local menu contains 30 items across 11 categories. The import archives the original demo dishes, retains other custom dishes, preserves all order snapshots, and does not overwrite existing TOSS edits on repeated runs. The local pre-import database is backed up at `.tools/pre-toss-menu.db` (ignored by Git).

## Prices

| Section | Item / portion | Price in rupees |
| --- | --- | --- |
| Crispy Tenders | 2 / 4 / 6 / 8 pieces | 149 / 189 / 259 / 319 |
| Wings | 2 / 4 / 6 / 8 pieces | 139 / 179 / 229 / 289 |
| Fried Chicken Bucket | 2 / 4 / 6 / 8 pieces | 119 / 229 / 319 / 449 |
| Burgers | Chicken Cluck / Nashville Cheese / Chicken Steak / Smash Chicken / Double Cheese / Triple Steak Stack | 169 / 189 / 199 / 199 / 239 / 299 |
| Loaded Fries | Peri Peri / Chicken Loaded / Nashville Cheese / Paneer Loaded | 149 / 169 / 189 / 179 |
| Wraps | Chicken Loaded / Nashville Chicken / Paneer / Mushroom | 169 / 189 / 179 / 149 |
| Mocktails | Blue Lagoon / Mint Mojito / Strawberry Mocktail | 119 each |
| Veg Burgers | Mushroom / Paneer | 159 / 179 |
| Veg Wraps | Paneer / Mushroom | 149 each |
| Veg Fries | Peri Peri / Cheese / Paneer Loaded | 99 / 129 / 169 |
| Combo Deals | Combo 1 / Combo 2 / Combo 3 | 329 / 349 / 379 |

The user explicitly confirmed the tender and bucket portion prices. Other prices were transcribed from the poster. Identically named dishes with different printed prices stay separate in their original categories; no attempt was made to infer different recipes. Descriptions are brief editorial summaries, not ingredient/allergen specifications.

Portions are required selections; sauce tossing is an optional +₹30 selection. Extra cheese costs ₹29 and an extra dip costs ₹19 on burgers. Combo orders require a choice of the three printed mocktails without an additional charge. All these groups are editable through administration.

Sauces: Cajun Mayo, Peri Peri Mayo, Chilli Garlic Mayo, Buffalo Sauce, Hot Honey Glaze, BBQ Ranch, Nashville Hot Cheese, Honey Mustard and Garlic Blaze.

Combo 1: Chicken Cluck Burger + fries + mocktail. Combo 2: four wings + loaded fries + mocktail. Combo 3: Chicken Loaded Wrap + fries + mocktail.

## Assets

Food photography is AI-generated decorative imagery, not a photograph of the truck's actual servings. Admin-uploaded product photos override the decorative card imagery. The logo is a code-rendered TOSS wordmark inspired by the reference, not an extracted original logo file. Anton is self-hosted with its SIL Open Font License.

See [asset files and exact generation prompts](frontend/public/images/ASSETS.md).

## Fresh and existing installations

Fresh installations seed the TOSS menu by default. To import it into an existing installation, run `python -m app.toss_menu` from `backend` with that installation's `DATABASE_URL`. The operation is transactional and preserves orders. Restarting the API is unnecessary; open clients refresh their menu within 15 seconds. Backend regression fixtures use `MENU_PROFILE=demo`; browser tests use the TOSS menu.
