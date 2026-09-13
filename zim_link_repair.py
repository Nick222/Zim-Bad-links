#!/usr/bin/env python3

import os
import re
import shutil
import sys

from zim.newfs import FilePath
from zim.notebook import build_notebook
from zim.notebook.page import HRef
from zim.parse.links import link_type


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

print("\nBuilding page-name index...\n")

pages_by_name = {}

for page_path in notebook.pages.walk():

    page = notebook.get_page(page_path)

    if not page.exists():
        continue

    name = page_path.parts[-1]

    pages_by_name.setdefault(
        name,
        []
    ).append(page_path)


print(
    f"Existing pages indexed: "
    f"{sum(len(v) for v in pages_by_name.values())}"
)

print(
    f"Unique page names: "
    f"{len(pages_by_name)}"
)


lost_count = 0
unique_candidate_count = 0
multiple_candidate_count = 0
no_candidate_count = 0

page_count = 0
link_count = 0

repaired_count = 0


print("\nScanning notebook...\n")


for source in notebook.pages.walk():

    page = notebook.get_page(source)

    if not page.exists():
        continue

    page_count += 1

    text = page.peek_get_source()

    if text is None:
        continue


    # All changes for this page are prepared in memory.
    new_text = text

    page_repairs = []


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

            if target_page.exists():
                continue


            lost_count += 1

            missing_name = target.parts[-1]

            candidates = pages_by_name.get(
                missing_name,
                []
            )


            # --------------------------------------------------
            # Multiple candidates
            # --------------------------------------------------

            if len(candidates) > 1:

                multiple_candidate_count += 1

                print(
                    "=================================================="
                )

                print("MULTIPLE CANDIDATES")

                print(
                    f"SOURCE:     {source}"
                )

                print(
                    f"OLD LINK:   [[{link}]]"
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

                continue


            # --------------------------------------------------
            # No candidate
            # --------------------------------------------------

            if len(candidates) == 0:

                no_candidate_count += 1

                print(
                    "=================================================="
                )

                print("NO CANDIDATE")

                print(
                    f"SOURCE:     {source}"
                )

                print(
                    f"OLD LINK:   [[{link}]]"
                )

                print(
                    f"MISSING:    {target}"
                )

                print()

                continue


            # --------------------------------------------------
            # Exactly one candidate
            # --------------------------------------------------

            unique_candidate_count += 1

            candidate = candidates[0]

            old_target = link.split('|', 1)[0]

            new_target = ':' + str(candidate)


            # --------------------------------------------------
            # Verify that the proposed new link resolves
            # exactly to the candidate.
            # --------------------------------------------------

            new_href = HRef.new_from_wiki_link(
                new_target
            )

            new_resolved = notebook.pages.resolve_link(
                source,
                new_href
            )

            if new_resolved != candidate:

                print(
                    "=================================================="
                )

                print("ERROR")

                print()

                print(
                    "New link does not resolve to candidate."
                )

                print(
                    f"SOURCE:     {source}"
                )

                print(
                    f"Expected:   {candidate}"
                )

                print(
                    f"Resolved:   {new_resolved}"
                )

                print()

                print(
                    "NO FILE WAS MODIFIED BY THIS CASE."
                )

                raise SystemExit(1)


            # --------------------------------------------------
            # Preserve the label, if present.
            # --------------------------------------------------

            if '|' in link:

                _, label = link.split('|', 1)

                new_link = (
                    f"{new_target}|{label}"
                )

            else:

                new_link = new_target


            old_full_link = f"[[{link}]]"

            new_full_link = f"[[{new_link}]]"


            # --------------------------------------------------
            # Safety check:
            # the exact old link must occur only once
            # in the original page.
            # --------------------------------------------------

            occurrence_count = text.count(
                old_full_link
            )

            if occurrence_count != 1:

                print(
                    "=================================================="
                )

                print("ERROR")

                print()

                print(
                    "Unexpected number of occurrences."
                )

                print(
                    f"SOURCE:     {source}"
                )

                print(
                    f"OCCURRENCES: {occurrence_count}"
                )

                print(
                    f"OLD LINK:   {old_full_link}"
                )

                print()

                print(
                    "ABORTING BEFORE WRITING THIS FILE."
                )

                raise SystemExit(1)


            # --------------------------------------------------
            # Apply this replacement only to the in-memory
            # version of the page.
            # --------------------------------------------------

            previous_text = new_text

            new_text = new_text.replace(
                old_full_link,
                new_full_link,
                1
            )


            if new_text == previous_text:

                print(
                    "=================================================="
                )

                print("ERROR")

                print()

                print(
                    "Replacement produced no change."
                )

                print(
                    f"SOURCE:     {source}"
                )

                print(
                    f"OLD LINK:   {old_full_link}"
                )

                print(
                    f"NEW LINK:   {new_full_link}"
                )

                print()

                raise SystemExit(1)


            page_repairs.append(
                (
                    old_target,
                    new_target,
                    old_full_link,
                    new_full_link
                )
            )


        except SystemExit:
            raise

        except Exception as error:

            print(
                "=================================================="
            )

            print("ERROR")

            print()

            print(
                f"SOURCE:     {source}"
            )

            print(
                f"LINK:       [[{link}]]"
            )

            print(
                f"ERROR:      {error}"
            )

            print()

            raise SystemExit(1)


    # ==========================================================
    # All links on this page have now been analysed.
    #
    # Nothing has been written yet.
    # ==========================================================

    if not page_repairs:
        continue


    # ----------------------------------------------------------
    # Show all repairs prepared for this page.
    # ----------------------------------------------------------

    print(
        "=================================================="
    )

    print(
        f"PAGE: {source}"
    )

    print()

    print(
        f"Repairs prepared: {len(page_repairs)}"
    )

    print()

    for (
        old_target,
        new_target,
        old_full_link,
        new_full_link
    ) in page_repairs:

        print(
            f"OLD LINK:   {old_full_link}"
        )

        print(
            f"NEW LINK:   {new_full_link}"
        )

        print()


    # ----------------------------------------------------------
    # Create exactly one backup for this page.
    # ----------------------------------------------------------

    source_file = page.source_file

    backup_file = FilePath(
        str(source_file) + ".bak"
    )


    if os.path.exists(str(backup_file)):

        print(
            "=================================================="
        )

        print("ERROR")

        print()

        print(
            f"Backup already exists:\n{backup_file}"
        )

        print()

        print(
            "ABORTING TO AVOID OVERWRITING THE BACKUP."
        )

        print()

        raise SystemExit(1)


    # ----------------------------------------------------------
    # Create backup before writing anything.
    # ----------------------------------------------------------

    shutil.copy2(
        str(source_file),
        str(backup_file)
    )


    # ----------------------------------------------------------
    # Write the complete page once.
    # ----------------------------------------------------------

    source_file.write(
        new_text
    )


    # ----------------------------------------------------------
    # Verify the written file.
    # ----------------------------------------------------------

    check_text = source_file.read()

    if check_text != new_text:

        print(
            "=================================================="
        )

        print("ERROR")

        print()

        print(
            "Written file does not match expected text."
        )

        print(
            f"SOURCE: {source}"
        )

        print()

        print(
            f"Backup remains available:\n{backup_file}"
        )

        print()

        raise SystemExit(1)


    repaired_count += len(page_repairs)


print(
    "=================================================="
)

print("REPAIR COMPLETE")

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
    f"Links repaired:             {repaired_count}"
)

print()

print(
    "Backup files were created for every modified page."
)
