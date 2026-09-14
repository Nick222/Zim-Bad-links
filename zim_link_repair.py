#!/usr/bin/env python3

import configparser
import os
import re
import shutil
import sys

from zim.newfs import FilePath
from zim.notebook import build_notebook
from zim.notebook.page import HRef
from zim.parse.links import link_type


# ==========================================================
# Command line
# ==========================================================

if len(sys.argv) not in (2, 3):

    print("Usage:")
    print(
        f'  python3 {sys.argv[0]} "/path/to/source/notebook"'
    )
    print(
        f'  python3 {sys.argv[0]} '
        f'"/path/to/source/notebook" "Target Notebook Name"'
    )

    sys.exit(1)


SOURCE_NOTEBOOK = sys.argv[1]

TARGET_NOTEBOOK_NAME = None

if len(sys.argv) == 3:
    TARGET_NOTEBOOK_NAME = sys.argv[2]


# ==========================================================
# Find target notebook in Zim configuration
# ==========================================================

def find_notebook(notebook_name):

    config_file = os.path.expanduser(
        "~/.config/zim/notebooks.list"
    )

    config = configparser.ConfigParser()

    config.read(config_file)

    for section in config.sections():

        if not section.startswith("Notebook "):
            continue

        name = config.get(
            section,
            "name",
            fallback=""
        )

        if name != notebook_name:
            continue

        uri = config.get(
            section,
            "uri",
            fallback=""
        )

        interwiki = config.get(
            section,
            "interwiki",
            fallback=""
        )

        path = os.path.abspath(
            os.path.expanduser(uri)
        )

        return {
            "name": name,
            "path": path,
            "interwiki": interwiki,
        }

    return None


# ==========================================================
# Open source notebook
# ==========================================================

print("Opening source notebook...")

notebook, href_from_location = build_notebook(
    FilePath(SOURCE_NOTEBOOK)
)

print("Source notebook opened:")
print(notebook)


# ==========================================================
# Open target notebook information
# ==========================================================

target_info = None

if TARGET_NOTEBOOK_NAME is not None:

    target_info = find_notebook(
        TARGET_NOTEBOOK_NAME
    )

    if target_info is None:

        print()
        print("ERROR")
        print()
        print(
            f'Notebook not found: "{TARGET_NOTEBOOK_NAME}"'
        )

        sys.exit(1)

    print()
    print("Target notebook:")
    print(
        f"Name:       {target_info['name']}"
    )
    print(
        f"Path:       {target_info['path']}"
    )
    print(
        f"Interwiki:  {target_info['interwiki']}"
    )


# ==========================================================
# Build index of existing pages in source notebook
# ==========================================================

print()
print("Building source page-name index...")
print()

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
    f"Existing source pages indexed: "
    f"{sum(len(v) for v in pages_by_name.values())}"
)

print(
    f"Unique source page names: "
    f"{len(pages_by_name)}"
)


# ==========================================================
# Build exact filename index for target notebook
#
# We deliberately search by filename, not by page path.
# Spaces in Zim page names are represented by underscores
# in filenames.
# ==========================================================

target_files_by_name = {}


if target_info is not None:

    print()
    print("Building target filename index...")
    print()

    target_root = target_info["path"]

    for root, directories, files in os.walk(
        target_root
    ):

        for filename in files:

            if not filename.endswith(".txt"):
                continue

            page_name = filename[:-4].replace(
                "_",
                " "
            )

            target_file = os.path.join(
                root,
                filename
            )

            target_files_by_name.setdefault(
                page_name,
                []
            ).append(
                target_file
            )

    print(
        f"Target page filenames indexed: "
        f"{sum(len(v) for v in target_files_by_name.values())}"
    )

    print(
        f"Unique target page names: "
        f"{len(target_files_by_name)}"
    )


# ==========================================================
# Scan source notebook
# ==========================================================

lost_count = 0

source_candidate_count = 0

target_candidate_count = 0
target_multiple_count = 0
target_no_candidate_count = 0

page_count = 0
link_count = 0

links_repaired = 0


print()
print("Scanning source notebook...")
print()


for source in notebook.pages.walk():

    page = notebook.get_page(source)

    if not page.exists():
        continue

    page_count += 1

    text = page.peek_get_source()

    if text is None:
        continue


    # ------------------------------------------------------
    # All repairs for THIS page are collected here.
    #
    # Nothing is written while individual links are scanned.
    # ------------------------------------------------------

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

            # ------------------------------------------------
            # IMPORTANT:
            # This is the original working diagnostic logic.
            # Do not replace it with custom link resolution.
            # ------------------------------------------------

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


            # ------------------------------------------------
            # Lost link
            # ------------------------------------------------

            lost_count += 1

            missing_name = target.parts[-1]


            # ==================================================
            # First: search inside the source notebook
            # ==================================================

            source_candidates = pages_by_name.get(
                missing_name,
                []
            )


            if len(source_candidates) == 1:

                source_candidate_count += 1

                candidate = source_candidates[0]

                old_link = f"[[{link}]]"


                # Preserve label after | exactly as it was.
                if '|' in link:

                    _, label = link.split(
                        '|',
                        1
                    )

                    new_link = (
                        f"[[{candidate}|{label}]]"
                    )

                else:

                    new_link = (
                        f"[[{candidate}]]"
                    )


                # The exact old link must occur once
                # in the original page.
                if text.count(old_link) != 1:

                    print()
                    print(
                        "ERROR: Exact old link occurs "
                        "more than once."
                    )
                    print(
                        f"SOURCE: {source}"
                    )
                    print(
                        f"OLD LINK: {old_link}"
                    )
                    print(
                        f"COUNT: {text.count(old_link)}"
                    )

                    continue


                page_repairs.append(
                    (
                        old_link,
                        new_link
                    )
                )


                print()
                print(
                    "=================================================="
                )
                print(
                    "SOURCE CANDIDATE FOUND"
                )
                print(
                    f"SOURCE:       {source}"
                )
                print(
                    f"OLD LINK:     {old_link}"
                )
                print(
                    f"MISSING PAGE: {target}"
                )
                print(
                    f"NEW LINK:     {new_link}"
                )

                continue


            # ==================================================
            # If no unique source candidate, optionally search
            # target notebook.
            # ==================================================

            if target_info is None:
                continue


            target_candidates = target_files_by_name.get(
                missing_name,
                []
            )


            if len(target_candidates) == 0:

                target_no_candidate_count += 1

                print(
                    "=================================================="
                )

                print(
                    "NO TARGET CANDIDATE"
                )

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


            if len(target_candidates) > 1:

                target_multiple_count += 1

                print(
                    "=================================================="
                )

                print(
                    "MULTIPLE TARGET CANDIDATES"
                )

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

                for candidate_file in target_candidates:

                    print(
                        f"              {candidate_file}"
                    )

                print()

                continue


            # ==================================================
            # Exactly one target file
            # ==================================================

            target_candidate_count += 1

            target_file = target_candidates[0]


            # --------------------------------------------------
            # Path relative to target notebook root
            # --------------------------------------------------

            relative_file = os.path.relpath(
                target_file,
                target_info["path"]
            )


            # --------------------------------------------------
            # Convert filesystem path back to Zim page path.
            # --------------------------------------------------

            relative_without_extension = os.path.splitext(
                relative_file
            )[0]


            target_page_path = (
                relative_without_extension
                .replace(
                    os.sep,
                    ":"
                )
                .replace(
                    "_",
                    " "
                )
            )


            # --------------------------------------------------
            # Construct interwiki link.
            # --------------------------------------------------

            new_target = (
                f"{target_info['interwiki']}?"
                f"{target_page_path}"
            )


            if '|' in link:

                _, label = link.split(
                    '|',
                    1
                )

                new_link = (
                    f"[[{new_target}|{label}]]"
                )

            else:

                new_link = (
                    f"[[{new_target}]]"
                )


            old_link = f"[[{link}]]"


            # The exact old link must occur once.
            if text.count(old_link) != 1:

                print()
                print(
                    "ERROR: Exact old link occurs "
                    "more than once."
                )
                print(
                    f"SOURCE: {source}"
                )
                print(
                    f"OLD LINK: {old_link}"
                )
                print(
                    f"COUNT: {text.count(old_link)}"
                )

                continue


            # --------------------------------------------------
            # IMPORTANT:
            # Do not write yet.
            # Add the repair to this page's batch.
            # --------------------------------------------------

            page_repairs.append(
                (
                    old_link,
                    new_link
                )
            )


            print(
                "=================================================="
            )

            print(
                "TARGET CANDIDATE FOUND"
            )

            print(
                f"SOURCE:         {source}"
            )

            print(
                f"OLD LINK:       {old_link}"
            )

            print(
                f"MISSING PAGE:   {target}"
            )

            print(
                f"TARGET FILE:    {target_file}"
            )

            print(
                f"TARGET PAGE:    {target_page_path}"
            )

            print(
                f"NEW LINK:       {new_link}"
            )

            print()


        except Exception as error:

            print(
                "=================================================="
            )

            print(
                "ERROR"
            )

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


    # ========================================================
    # Apply all repairs for this page in memory
    # ========================================================

    if not page_repairs:
        continue


    new_text = text


    for old_link, new_link in page_repairs:

        if new_text.count(old_link) != 1:

            print()
            print(
                "ERROR: Link occurrence changed "
                "unexpectedly."
            )

            print(
                f"SOURCE: {source}"
            )

            print(
                f"OLD LINK: {old_link}"
            )

            print(
                f"COUNT: {new_text.count(old_link)}"
            )

            print(
                "Page was NOT modified."
            )

            new_text = None

            break


        new_text = new_text.replace(
            old_link,
            new_link,
            1
        )


    if new_text is None:
        continue


    # ========================================================
    # One backup for the whole page
    # ========================================================

    source_file = page.source_file

    backup_file = FilePath(
        str(source_file) + ".bak"
    )


    if os.path.exists(str(backup_file)):

        print()
        print(
            "ERROR: Backup file already exists."
        )

        print(
            f"FILE:   {source_file}"
        )

        print(
            f"BACKUP: {backup_file}"
        )

        print(
            "Page was NOT modified."
        )

        continue


    # ========================================================
    # Create backup
    # ========================================================

    try:

        shutil.copy2(
            str(source_file),
            str(backup_file)
        )

    except Exception as error:

        print()
        print(
            "ERROR CREATING BACKUP."
        )

        print(
            f"FILE:  {source_file}"
        )

        print(
            f"ERROR: {error}"
        )

        continue


    # ========================================================
    # Write page ONCE
    # ========================================================

    try:

        source_file.write(
            new_text
        )

    except Exception as error:

        print()
        print(
            "ERROR WRITING PAGE."
        )

        print(
            f"FILE:  {source_file}"
        )

        print(
            f"ERROR: {error}"
        )

        continue


    # ========================================================
    # Verify written content
    # ========================================================

    try:

        written_text = source_file.read()

    except Exception as error:

        print()
        print(
            "ERROR READING PAGE AFTER WRITE."
        )

        print(
            f"FILE:  {source_file}"
        )

        print(
            f"ERROR: {error}"
        )

        continue


    if written_text != new_text:

        print()
        print(
            "ERROR: Verification failed!"
        )

        print(
            f"FILE: {source_file}"
        )

        print(
            "Written content differs from expected content."
        )

        continue


    links_repaired += len(
        page_repairs
    )


    print(
        "--------------------------------------------------"
    )

    print(
        "PAGE REPAIRED"
    )

    print(
        f"SOURCE:         {source}"
    )

    print(
        f"LINKS REPAIRED: {len(page_repairs)}"
    )

    print(
        f"BACKUP:         {backup_file}"
    )

    print()


# ==========================================================
# Summary
# ==========================================================

print(
    "=================================================="
)

print(
    "SCAN / REPAIR COMPLETE"
)

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
    f"Unique source candidate:    {source_candidate_count}"
)


if target_info is not None:

    print(
        f"Unique target candidate:    {target_candidate_count}"
    )

    print(
        f"Multiple target candidates: {target_multiple_count}"
    )

    print(
        f"No target candidate:        {target_no_candidate_count}"
    )


print()

print(
    f"Links repaired:             {links_repaired}"
)
