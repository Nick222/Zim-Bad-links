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

print(
    "Usage:"
)

print(
    f"  python3 {sys.argv[0]} \"/path/to/notebook\""
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
# Scan notebook
# ------------------------------------------------------------

lost_count = 0
unique_candidate_count = 0
multiple_candidate_count = 0
no_candidate_count = 0

page_count = 0
link_count = 0

replacement_count = 0
multiple_occurrence_count = 0

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


        if not target_page.exists():

            lost_count += 1

            missing_name = target.parts[-1]

            candidates = pages_by_name.get(
                missing_name,
                []
            )


            # ------------------------------------------------
            # Exactly one possible replacement
            # ------------------------------------------------

            if len(candidates) == 1:

                unique_candidate_count += 1


                old_target = link.split('|', 1)[0]

                new_target = ':' + str(candidates[0])


                # ------------------------------------------------
                # Verify that Zim resolves the new link
                # correctly.
                # ------------------------------------------------

                new_href = HRef.new_from_wiki_link(
                    new_target
                )

                new_resolved = notebook.pages.resolve_link(
                    source,
                    new_href
                )

                if new_resolved != candidates[0]:

                    print(
                        "!!! NEW LINK RESOLUTION ERROR !!!"
                    )

                    print(
                        f"Expected: {candidates[0]}"
                    )

                    print(
                        f"Resolved: {new_resolved}"
                    )

                    print()

                    continue


                # ------------------------------------------------
                # Build the replacement while preserving
                # everything after the first '|'.
                # ------------------------------------------------

                if '|' in link:

                    _, label = link.split('|', 1)

                    new_link = (
                        f"{new_target}|{label}"
                    )

                else:

                    new_link = new_target


                old_full_link = f"[[{link}]]"

                new_full_link = f"[[{new_link}]]"


                # ------------------------------------------------
                # Perform replacement only in memory.
                # Nothing is written to disk.
                # ------------------------------------------------

                occurrence_count = text.count(
                    old_full_link
                )

                if occurrence_count > 1:

                    multiple_occurrence_count += 1

                    print(
                        "!!! MULTIPLE OCCURRENCES !!!"
                    )

                    print(
                        f"Source: {source}"
                    )

                    print(
                        f"Occurrences: {occurrence_count}"
                    )

                    print()


                new_text = text.replace(
                    old_full_link,
                    new_full_link
                )


                if new_text != text:

                    replacement_count += occurrence_count


                # ------------------------------------------------
                # Preview
                # ------------------------------------------------

                print(
                    f"OLD LINK__: [[{old_target}|...]]"
                )

                print(
                    f"NEW LINK__: [[{new_target}|...]]"
                )

                print()


            # ------------------------------------------------
            # More than one possible replacement
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
                    f"OLD LINK: [[{old_link}|...]]"
                )

                print(
                    f"MISSING:     {target}"
                )

                print()

                for candidate in candidates:

                    print(
                        f"              {candidate}"
                    )

                print()


            # ------------------------------------------------
            # No possible replacement
            # ------------------------------------------------

            else:

                no_candidate_count += 1

                print(
                    "=================================================="
                )

                print("NO CANDIDATE")

                old_link = link.split('|', 1)[0]

                print(
                    f"OLD LINK: [[{old_link}|...]]"
                )

                print(
                    f"MISSING:     {target}"
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
f"Replacements prepared:      {replacement_count}"
)

print(
f"Pages with repeated links:  {multiple_occurrence_count}"
)

print()

print(
"NOTE: No files were modified."
)
