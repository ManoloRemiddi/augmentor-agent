<!-- Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0 -->

# Desktop colors and skins

Open **⋯ → Colors & skins**, also available from the compact-view menu.
The picker contains **Custom**, **Futuristic**, **Blossom lake**, and your saved
skins. Woodland and Moonlit Garden have been retired from the built-in list.
Existing user-created skin records remain available.

## Create a skin from an image

Choose **Upload background…**, then select a PNG, JPEG, or WebP. The image becomes
the panel background immediately, and its colours generate the panel hue, accent,
saturation, headings, links, and emphasis colours. Your light/dark choice and
activity effect stay selected. Butterflies also take their colours from the selected image, for both glitter and
larger wings. Changing the background updates them without resetting their flight.
Palette generation runs locally with no network
requests. You can adjust the resulting colours with the existing controls.

Choose **Save as…** to keep the result as a named skin. Uploads are copied into the
appearance preferences, so moving or deleting the original file does not break
the skin. **Export…** embeds the image and appearance in one `.augmentor-skin.json`
file; the recipient uses **Import…**. Import conflicts prompt for a new name.

Uploads accept files up to 20 MiB and 32 megapixels. A local display copy is
normalised to JPEG, at most 1600 pixels per side; the source file is unchanged.
Transparent pixels are composited over a dark neutral background. Choose
**Background → Plain** to remove the current uploaded background, or **Blossom
lake** to use the bundled landscape. Save your uploaded skin before switching
backgrounds if you want to return to it.

## Effects

**Butterfly glitter** uses 420 tiny multicoloured butterflies (160 in compact view).
**Butterflies · 3× larger** keeps the same population and mouse interaction with
larger wings. They wander near the perimeter, scatter in the mouse wake, then drift
back. Disabling animation leaves a static busy indicator. Disabling activity effects
hides the indicator; the background remains. Futuristic retains plasma and flares.

**Reset** restores Futuristic, retaining the saved library and runtime settings.

## Sharing contract

Version 1 skins have no embedded upload; version 2 skins embed a validated raster
in `appearance.background_image` as base64. The `background` value is `none`,
`blossom-lake`, or `uploaded`. Older files missing background fields still import.
Version 2 requires this updated desktop app. Files above 6 MiB and unsupported
fields, effects, image formats, dimensions, or malformed image data are rejected
before application. No executable renderers, external paths, URLs, credentials,
conversation data, or model settings are exported. The library holds 100 skins.

Blossom lake uses the user-supplied September 16 landscape, copied unchanged to
`assets/blossom-lake.png`. No new licensing claim is made for that artwork. Its
built-in identifier refers to the image bundled with the receiving app.

This functionality is implemented in the native Desktop UI. The browser edition
and an online skin gallery are outside this implementation.
