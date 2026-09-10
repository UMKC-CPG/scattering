# Pseudocode — Index

> **Document hierarchy:** VISION → ARCHITECTURE → DESIGN →
> **PSEUDOCODE** → Code. For the rationale behind these algorithms
> see the corresponding section under `design/`.

---

**This file is an index, not the pseudocode.** Each numbered section
lives in its own file under `dev/pseudocode/`. Read this table to
find the section you need, then read only that file.

**This is the gate.** No file under `src/` is edited until the
governing section here exists and already describes the change. See
"Chain Discipline" in `../CLAUDE.md`. When beginning a coded task,
name the section from this table that governs it.

## Sections

| # | File | Governs | Design | Status |
| --- | --- | --- | --- | --- |
| 1 | [`01-topic-one.md`](pseudocode/01-topic-one.md) | `project` | 1 | draft |

<!-- Add a row here in the SAME edit that creates the file.

     "Governs" names the source files this section specifies; it is
     what makes the gate answerable in the other direction, letting a
     reader holding a source file find the section above it. Keep it
     current when code moves.

     Status is one of: draft, reviewed, implemented, superseded. -->

## Conventions

**Section numbers track DESIGN where they can.** Pseudocode section N
implements design section N by default. Where one design section
needs several algorithms, use N.1, N.2 rather than breaking the
correspondence, and say so in the Design column.

**Use the names the code will use.** The variable names here should
be the ones that appear in `src/`, following the naming rules in
`../CLAUDE.md`. Pseudocode that renames everything cannot be checked
against the implementation by eye, which is the whole point of it.

**Language-agnostic, but concrete.** No language syntax, but no
hand-waving either: loop bounds, index origins, allocation, and error
paths are all specified. "Compute the overlap" is not pseudocode.

**Never edit upward to match code.** A disagreement between this
document and the source means the source is wrong, unless the source
has first been verified against DESIGN. See `../CLAUDE.md`.
