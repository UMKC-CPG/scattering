# Task List

> **Document hierarchy:** this is a work queue, not a level of the
> chain. Tasks are organized by the level they affect, and each item
> cites the document section it touches.

---

## How to write an entry

```
- [ ] (D3.2) One-line statement of what must be true when done.
      Any constraint or gotcha the doer needs. Blocked by: (P1.4).
```

The leading tag is the citation: `V4` for VISION section 4, `A2` for
ARCHITECTURE 2, `D3.2` for design section 3.2, `P1.4` for pseudocode
1.4, and a path for code. An entry with no citation is an entry
nobody can check against anything.

**Keep entries short on purpose.** When a task's plan grows detailed
enough to implement from — naming the functions, the files, and the
call sequence — that specificity belongs in a `pseudocode/` section,
not here. A detailed TODO entry looks like a specification and is
not one: `/refine` never checks it against DESIGN, and once its box
is ticked nobody reads it again. Move the detail up and leave the
entry pointing at the section. This is the single most common way
this chain has been broken in practice.

Completed items move to ARCHIVE with a `- [x]`, keeping their
numbering so older cross-references still resolve.

---

## VISION

<!-- Goals and principles. -->

---

## ARCHITECTURE

<!-- Layout, modules, build, entry points. -->

---

## DESIGN

<!-- Algorithms, data structures, mathematical foundations. -->

---

## PSEUDOCODE

<!-- Algorithm specifications. Note that "write the pseudocode for
     X" is itself a task, and on this chain it is the task that must
     precede the corresponding CODE entry. -->

---

## CODE

<!-- Implementation. Every entry here should be able to name the
     pseudocode section that governs it. -->

---

## Campaigns

<!-- Long, bounded hunts through the whole code base for one class of
     problem — bugs, performance, security, a large imported body of
     code being brought up to standard — do not fit the five-level
     partition, because they cut across all of it.

     Give each campaign its own section below, or its own ledger file
     in dev/ once it outgrows a section (see dev/README.md). Do not
     force them into the level sections: on an earlier project this
     was left too late and the level sections silently became a mix
     of design work and bug triage, which made the whole list
     unreadable.

     Delete this heading if the project has no campaigns. -->

---

## ARCHIVE

<!-- Resolved items, newest first. Keep them: the archive is the only
     record of what was tried and rejected at the task level. -->
