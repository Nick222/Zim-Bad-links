#!/usr/bin/env python3

import re
import sys

from zim.newfs import FilePath
from zim.notebook import build_notebook
from zim.notebook.page import HRef
from zim.parse.links import link_type


# ------------------------------------------------------------
# Notebook path from command line
# ------------------------------------------------------------

if len(sys.argv) != 2:

    print("Usage:")
    print(
        f'  python3 {sys.argv[0]} "/path/to/notebook"'
    )

    sys.exit(1)


NOTEBOOK = sys.argv[1]


print("Opening notebook...")

notebook, href_from_location = build_notebook(
    FilePath(NOTEBOOK)
)

print("Notebook opened:")
print(notebook)


# ------------------------------------------------------------
# Build an index of existing pages by their final page name.
# ------------------------------------------------------------

print("\nBuilding page-name index...\n")

pages_by_name = {}

for page_path in notebook.pages.walk():

    page = notebook.get_page(page_path)

    if not page.exists():
        continue

    name = page_path.parts[-1]

    pages_by_name.setdefault(name, []).append(page_path)


print(
    f"Existing pages indexed: "
    f"{sum(len(v) for v in pages_by_name.values())}"
)

print(
    f"Unique page names: "
    f"{len(pages_by_name)}"
)


# ------------------------------------------------------------
# Statistics
# ------------------------------------------------------------

lost_count = 0
unique_candidate_count = 0
multiple_candidate_count = 0
no_candidate_count = 0

page_count = 0
link_count = 0


# ------------------------------------------------------------
# Scan notebook
# ------------------------------------------------------------

print("\nScanning notebook...\n")


for source in notebook.pages.walk():

    page = notebook.get_page(source)

    if not page.exists():
        continue

    page_count += 1

    text = page.peek_get_source()

    if text is None:
        continue


    links = re.findall(
        r'(?<!\[)\[\[([^\[\]]+)\]\]',
        text
    )


    for link in links:

        target_text = link.split('|', 1)[0]

        if not target_text:
            continue

        if link_type(target_text) != 'page':
            continue

        link_count += 1


        try:

            href = HRef.new_from_wiki_link(
                target_text
            )

            target = notebook.pages.resolve_link(
                source,
                href
            )

            target_page = notebook.get_page(
                target
            )


            # ------------------------------------------------
            # Existing link -- nothing to do.
            # ------------------------------------------------

            if target_page.exists():
                continue


            lost_count += 1

            missing_name = target.parts[-1]

            candidates = pages_by_name.get(
                missing_name,
                []
            )


            # ------------------------------------------------
            # Exactly one possible replacement.
            # ------------------------------------------------

            if len(candidates) == 1:

                unique_candidate_count += 1

                old_target = link.split('|', 1)[0]

                new_target = ':' + str(candidates[0])

                print(
                    f"OLD LINK__: [[{old_target}|...]]"
                )

                print(
                    f"NEW LINK__: [[{new_target}|...]]"
                )

                print()


            # ------------------------------------------------
            # More than one possible replacement.
            # ------------------------------------------------

            elif len(candidates) > 1:

                multiple_candidate_count += 1

                print(
                    "=================================================="
                )

                print("MULTIPLE CANDIDATES")

                print(
                    f"SOURCE:     {source}"
                )

                old_link = link.split('|', 1)[0]

                print(
                    f"OLD LINK:   [[{old_link}|...]]"
                )

                print(
                    f"MISSING:    {target}"
                )

                print()

                for candidate in candidates:

                    print(
                        f"              {candidate}"
                    )

                print()


            # ------------------------------------------------
            # No possible replacement.
            # ------------------------------------------------

            else:

                no_candidate_count += 1

                print(
                    "=================================================="
                )

                print("NO CANDIDATE")

                old_link = link.split('|', 1)[0]

                print(
                    f"OLD LINK:   [[{old_link}|...]]"
                )

                print(
                    f"MISSING:    {target}"
                )

                print()


        except Exception as error:

            print(
                "=================================================="
            )

            print("ERROR")

            old_link = link.split('|', 1)[0]

            print(
                f"OLD LINK: [[{old_link}|...]]"
            )

            print(
                f"ERROR:       {error}"
            )

            print()

            raise SystemExit(1)


# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------

print(
    "=================================================="
)

print("SCAN COMPLETE")

print(
    "=================================================="
)

print(
    f"Pages scanned:              {page_count}"
)

print(
    f"Page links checked:         {link_count}"
)

print(
    f"Lost links found:           {lost_count}"
)

print()

print(
    f"Unique candidate:           {unique_candidate_count}"
)

print(
    f"Multiple candidates:        {multiple_candidate_count}"
)

print(
    f"No candidate:               {no_candidate_count}"
)

print()

print(
    "NOTE: No files were modified."
)
