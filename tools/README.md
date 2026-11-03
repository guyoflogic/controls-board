# Controls Board TV display – build tools

Used by the "Controls Board – TV Publish" scheduled task in Claude.

- `build_display.py` turns an export of the Controls Work Board database into the TV page.
  It keeps only first names, task numbers, project codes, titles, status, priority,
  due dates and short update lines. No emails, work scopes or site addresses.
- `display-template.html` is the page design. The script puts the data in place of `__BOARD_DATA__`.

The published page lives on the `gh-pages` branch (index.html only) and is served by GitHub Pages.
To change the design, replace `display-template.html` here; the next hourly run picks it up.
