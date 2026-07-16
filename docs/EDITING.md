# Editing the profile

## The only file normally edited

Open `profile.toml` and change the values on the right side of the card.

Do not hand-edit:

- `light_mode.svg`
- `dark_mode.svg`
- `assets/portrait_ascii.txt`
- `assets/portrait_paths.svgfrag`
- `templates/profile.svg.tpl`

## Local preview

Python 3.11 or newer is required.

```bash
python scripts/render_profile.py
```

Then open `light_mode.svg` and `dark_mode.svg` in a browser.

To use current public GitHub statistics:

```bash
python scripts/render_profile.py --fetch-stats
```

Authentication is optional for local use. In GitHub Actions, the built-in
`GITHUB_TOKEN` is supplied automatically.

## How the pieces are separated

- `profile.toml`: biography, links and fallback statistics
- `assets/`: stable portrait
- `templates/`: stable visual design
- `scripts/render_profile.py`: renderer and GitHub statistics fetcher
- `light_mode.svg` / `dark_mode.svg`: generated files displayed by GitHub

Changing biography text does not modify the portrait or design source. The
renderer only regenerates the final display SVG files.

## First installation

1. Copy all files into the local profile repository on `profile-readme`.
2. Delete the older experimental files that are not present in this package.
3. Run `python scripts/render_profile.py --fetch-stats`.
4. Review both SVGs.
5. Commit and push `profile-readme`.
6. Open a pull request into `main`.
7. After merging, the scheduled workflow will refresh the public statistics daily.
