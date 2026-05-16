# guacamole-branding-plugin

A custom branding extension for [Apache Guacamole](https://guacamole.apache.org/) that applies a dark/light theme, custom fonts, and organisation-specific assets — deployed as a standard Guacamole extension (`.jar`).


## What it does

| Area | Detail |
|---|---|
| **Theme** | Full dark mode by default; automatically switches to light mode via `prefers-color-scheme` |
| **Accent colour** | Single `--accent` CSS variable controls all interactive elements (buttons, links, focus rings) |
| **Typography** | Inter (woff2, Regular + Bold) replaces the default Guacamole typeface |
| **Adaptive icons** | Touchscreen and touchpad setting icons swap between dark/light variants at runtime |
| **Translation Refs** | Patches AngularJS `$translate.instant` to resolve `@:key` linked translation references |


## Customising the theme

All design variables live in [`branding/css/themes.css`](branding/css/themes.css). There are two blocks:

- **`:root`** — dark mode defaults (active whenever `prefers-color-scheme` is dark or unset)
- **`@media (prefers-color-scheme: light) { :root { … } }`** — light mode overrides

The accent colour used across buttons, links, tabs, and focus rings is controlled by a single set of variables:

```css
--accent:        #006fff;   /* primary */
--accent-hover:  #1a7fff;
--accent-active: #0060e0;
--accent-glow:   rgba(0, 111, 255, 0.20);
--accent-subtle: rgba(0, 111, 255, 0.12);
```

Change `--accent` and its companions in `themes.css` — no other file needs to be touched.


## Deploying

The deploy script zips the `branding/` folder into a `.jar`, uploads it to the Guacamole extensions directory over SFTP, and restarts the required services.

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create the config file

Copy the template and fill in your server details:

```bash
cp scripts/deploy.json.example scripts/deploy.json
```

`scripts/deploy.json` is listed in `.gitignore` because it contains credentials and should not be committed.

**Config reference:**

```jsonc
{
    "folder": "./branding",          // source folder to package
    "output_name": "branding.jar",   // output filename
    "keep_archive": false,           // keep the local .jar after upload
    "force_overwrite": false,        // true  = overwrite remote file silently
                                     // false = prompt before overwriting (default)
    "server": {
        "host": "192.168.1.10",
        "port": 22,
        "username": "...",
        "password": "...",
        "remote_dir": "/etc/guacamole/extensions"
    }
}
```

### 3. Run

```bash
python scripts/deploy.py
```

If `force_overwrite` is `false` (the default) and a file already exists at the remote path, you will be prompted:

```
  '/etc/guacamole/extensions/branding.jar' already exists on 192.168.1.10. Overwrite? [y/N]
```

The script restarts `guacd` and `tomcat9` automatically after a successful upload.


## Extension structure

Guacamole loads extensions from the `extensions/` directory as zip archives with a `.jar` extension. The manifest (`guac-manifest.json`) declares which CSS, JS, translation, and resource files the extension provides. Assets are served by Guacamole's built-in resource handler and referenced in CSS/JS using the extension namespace path `app/ext/branding/`.


## Third-party assets

| Asset | Source | License |
|---|---|---|
| Inter typeface | [rsms/inter](https://github.com/rsms/inter) | SIL Open Font License 1.1 |
