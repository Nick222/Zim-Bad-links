# Zim Lost Links Tools

Two small Python utilities for finding and repairing broken internal page links in a [Zim Desktop Wiki](https://zim-wiki.org/) notebook.

These tools are intended for a specific but common situation: a Zim page was moved to another location in the notebook, but its page name was not changed. Existing links still point to the old location and therefore become broken.

The tools use Zim's own link-resolution mechanism rather than trying to reproduce Zim's link semantics independently.

## The problem

Suppose a link originally points to:

```text
:1 Дневник:2021:01:02:Some Page
```

and the page is later moved to:

```text
:1 Дневник:2021:02:06:Some Page
```

The page name (`Some Page`) remains the same, but the old link no longer resolves to an existing page.

Zim represents such a target as a page that does not currently exist. The page may appear in the interface as an ephemeral/placeholder page.

If there are many such links in a large notebook, finding and repairing them manually can be difficult.

## `zim_lost_links.py`

This is the **diagnostic** tool.

It scans the notebook for internal page links and checks whether each link resolves to an existing page.

For every broken link, it takes the final page-name component of the target and searches the notebook for existing pages with the same final name.

The result is classified into three cases:

### 1. Exactly one candidate

If exactly one existing page has the same final page name, the tool reports it as a possible repair.

For example:

```text
OLD LINK:   [[:1 Дневник:2021:01:02:Some Page|...]]
NEW LINK:   [[:1 Дневник:2021:02:06:Some Page|...]]
```

The tool does **not** modify the notebook.

### 2. Multiple candidates

If several pages have the same final name, the tool does not guess.

It lists all candidates and leaves the broken link unchanged.

This is important because a page name such as `03`, `Introduction`, or `Results` may legitimately occur in many different parts of a notebook.

### 3. No candidate

If no existing page has the same final name, the link is reported but no automatic repair is proposed.

This may indicate that the page was renamed, deleted, or is otherwise not recoverable by this method.

## `zim_link_repair.py`

This is the **repair** tool.

It uses the same detection logic as `zim_lost_links.py`, but automatically repairs only the safest cases:

* the target page does not exist;
* exactly one existing page has the same final page name;
* the proposed new link is independently checked using Zim's own link resolver;
* the original link occurs exactly once in the source page.

Before modifying a page, the tool creates a `.bak` backup of the original file.

Existing `.bak` files are never overwritten. If a backup already exists, the tool stops rather than risking loss of the original data.

After writing the repaired page, the tool reads the file back and verifies that the resulting contents are exactly what was expected.

## Link labels are preserved

If a link contains a display label:

```text
[[old:path|My description]]
```

the repair changes only the target:

```text
[[new:path|My description]]
```

The original label is preserved unchanged.

## Zim link semantics

The tools deliberately use Zim's own link parser and resolver.

This is important because Zim supports several kinds of page references, including relative links and links beginning with `+` for subpages.

For example:

```text
[[+A Размышления]]
```

does not simply mean "find a page named `A Размышления` anywhere in the notebook". It refers to a subpage relative to the current page.

Therefore the tools do **not** blindly replace every broken link with a page having the same final name.

Only an unambiguous candidate is automatically repaired.

Ambiguous cases are reported for manual inspection.

## Requirements

* Linux or another system with Python 3
* Zim Desktop Wiki
* Zim's Python modules available to Python

The scripts were developed and tested with Zim 0.77.x.

## Usage

Both scripts accept the notebook path as a command-line argument.

### Find broken links

```bash
python3 zim_lost_links.py "/path/to/your/notebook"
```

Example:

```bash
python3 zim_lost_links.py "/home/user/My Notebook"
```

This script is read-only and does not modify any notebook files.

### Repair broken links

```bash
python3 zim_link_repair.py "/path/to/your/notebook"
```

Example:

```bash
python3 zim_link_repair.py "/home/user/My Notebook"
```

The repair tool modifies only pages for which it has found exactly one unambiguous candidate. A backup file is created before every modification.

## Recommended workflow

For safety, run the tools in this order:

1. Run `zim_lost_links.py`.
2. Examine the reported broken links and proposed candidates.
3. Make sure the proposed repairs are correct.
4. Run `zim_link_repair.py`.
5. Run `zim_lost_links.py` again to check the result.

The diagnostic script is especially useful as a final verification step.

## What these tools deliberately do not do

These scripts are not a general-purpose "guess where a page was moved" system.

They do not attempt to determine that:

```text
Old Page Name
```

was renamed to:

```text
New Page Name
```

Such cases cannot be reliably distinguished from deleted pages or unrelated pages with similar names.

The purpose of these utilities is narrower:

> **Find broken links whose target page was moved without changing its page name, and safely repair them when the destination is unambiguous.**

This conservative approach is intentional. When there is uncertainty, the tools report the problem instead of guessing.
