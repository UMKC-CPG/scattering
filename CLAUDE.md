# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when
working with code in this repository.

> **Session setup:** run `/color purple` and `/rename SCATTERING` at
> the start of each session so that concurrent sessions on different
> projects stay visually distinct in the terminal.

## Document Hierarchy

This project uses a five-level document chain. All design documents
live in `dev/`. Read them in order when starting work:

1. `dev/VISION.md` — goals, principles, non-negotiables
2. `dev/ARCHITECTURE.md` — layout, modules, dependencies
3. `dev/DESIGN.md` — algorithms, data structures, math
4. `dev/PSEUDOCODE.md` — language-agnostic algorithm specs
5. Source code in `src/`

`dev/TODO.md` tracks tasks organized by level. Use `/focus` to start
a session and `/refine` to check consistency across the chain.

**DESIGN and PSEUDOCODE are split across files.** `dev/DESIGN.md` and
`dev/PSEUDOCODE.md` are *indexes*: each numbered section lives in its
own file under `dev/design/` or `dev/pseudocode/`. This is deliberate.
On earlier projects these documents reached 800 KB as single files, at
which point no reader — human or machine — could load one to change a
paragraph, and every edit risked collateral damage elsewhere in the
file. Read the index to find the section, then read only that file.

When you add a section, create its file AND add its row to the index
in the same edit. An index that has drifted from the directory is the
one failure mode this layout introduces, and `/refine` checks for it.

`dev/README.md` describes everything else that lives in `dev/` and
which of it is, and is not, part of the chain.

## Chain Discipline: No Code Without Pseudocode

The chain runs downward: VISION → ARCHITECTURE → DESIGN → PSEUDOCODE
→ code. A new feature enters at the top and flows down. Each level is
the specification for the one below it, and each is written before
that one exists.

**The gate.** Before editing any file under `src/`, the governing
PSEUDOCODE section must already exist and must already describe the
change. If it does not, stop and write it first, and say so plainly
rather than proceeding and back-filling afterward. A back-filled level
is not a level: nobody reviewed the code against it, so it records
what was built rather than specifying what should have been.

**Announce the level.** When beginning a coded task, name the
PSEUDOCODE section that governs it before touching `src/`. Being
unable to name one is itself the answer — the pseudocode is missing
and must be written.

**A detailed TODO entry is not pseudocode.** This is the trap that
has actually caught us. A task entry that names the functions, the
files, and the call sequence reads like a specification and is
detailed enough to code from directly. It is not a level of the chain.
It is never checked against DESIGN by `/refine`, and once its box is
ticked it is never read again. When a task's plan grows specific
enough to implement from, that specificity belongs in PSEUDOCODE —
move it there and leave the TODO entry pointing at the section.

**Why this matters more than it looks.** The chain is what lets a
reader who has been away trust the source. Code with a pseudocode
section above it can be checked against a spec that a human agreed
to. Code without one can only be checked against itself, which is no
check at all. Skipping the level costs nothing on the day it is
skipped and costs the project its reviewability forever after.

**The one legitimate upward edit.** Pseudocode may be brought into
agreement with existing code only where that code has first been
verified to implement DESIGN faithfully. Anywhere else, a
disagreement between pseudocode and code means the *code* is wrong.
Never edit the pseudocode to match code merely because the code is
already written.

**New work grafted onto existing code needs a seam inventory.**
Writing a level from the level above is sufficient only when the new
work is a new subsystem. When it must attach to a running program,
the lower levels take that program as a SECOND input, and a graft
point specified without reading the code on the other side of it is
specified from imagination.

So a DESIGN or PSEUDOCODE section that modifies existing code is not
finished until it names, for every quantity the new code consumes or
produces: where it comes from, who allocates it, who loads it, and
when. Write that inventory into the section. It is what a later
reader checks the prose against, and it is where specification errors
have actually occurred on earlier projects — every one of them at a
boundary with a routine nobody had read, none of them in the
algorithm itself.

The inventory also settles structure that would otherwise look like
taste. If a quantity is loaded inside an existing loop, a new
consumer of it has to sit in that loop; that is a consequence of the
seam, not a preference.

**Verify the section you are copying from.** Modelling new pseudocode
on an existing section propagates that section's defects sideways
into work that then looks independently derived. Check the model
section against its own code first.

## Level Awareness

During development conversations, the programmer may shift between
levels of the design chain without explicitly noticing. For example,
a discussion about a code fix may drift into questioning an
algorithm's design, or a design discussion may surface a conflict
with a core principle.

When you notice the conversation has moved to a different level than
where it started, say so briefly. For example: "This sounds like it's
becoming an ARCHITECTURE question — should we capture it there before
continuing with the code?" The goal is awareness, not interruption.
Let the programmer decide whether to switch context, propagate the
change to the appropriate document, or stay focused and defer.

Do not enforce rigid boundaries. The levels exist to organize
thinking, not to prevent it. A developer who is on a productive train
of thought should not be stopped — but when the thought resolves,
help them recognize which documents it touches so nothing is left
inconsistent.

## Secondary Agents and Forks

Do NOT spin up secondary agents, forks, or background subagents to
edit documents or code without the programmer's explicit say-so.
Asking is mandatory, and it must be a plain, visible question — "Do
you want me to fan this out to a separate agent, or should I just do
it inline here?" — never buried inside an obtuse command or a
multi-step sequence the programmer cannot easily see and veto.

The default for any bounded edit (a known set of spots across a few
files) is to do it INLINE in the main thread, one edit at a time, so
the programmer can follow along. Forks are expensive (they clone the
whole conversation context) and confusing to watch alongside the main
thread. Reserve them for genuinely parallel work or broad read-only
searches, and only after an explicit, transparent yes.

## Coding Style

### Line Length

Lines MUST NOT exceed 80 characters. This is a hard limit.

Short statements whose content is naturally brief (`implicit none`,
`endif`, `return`) are fine at their natural length — there is
nothing to fill them with. The rule applies when content is
available: long expository comments, argument lists, complex
expressions, and so on.

**Common failure mode — do not do this:**
```fortran
   ! Guard each deallocation because
   !   this subroutine is called from
   !   multiple program paths.
```
Those three ~35-character lines have plenty of content to fill longer
lines. Write them as:
```fortran
   ! Guard each deallocation because this subroutine is called
   !   from multiple program paths.
```
The idea: let each line run toward 80 before wrapping. Do not break
at natural phrase boundaries when the line is only at 40-50
characters. The result will be fewer, fuller lines — not lines padded
with filler.

`/lint` audits and mechanically repairs both violations; see
"Reflow Tooling" below.

### Documentation and Naming

CRITICAL: All program code must include rich, expressive
documentation so that students reading the source can easily follow
what is happening. Every function, class, and non-trivial block
should carry clear explanatory comments or docstrings that describe
purpose, inputs, outputs, and any relevant physics or math.

Variable names must be readable and self-documenting. Avoid cryptic
one- or two-letter abbreviations. Prefer concise but meaningful names
that a reader can understand without cross-referencing a legend.
Slightly-too-long names are far better than opaque short ones.

Good naming examples for an electronic structure program:
- `elec_mom` instead of `em` or `electron_momentum`
- `nuc_pot` instead of `np` or `nuclear_potential`
- `grid_spacing` instead of `gs` or `the_spacing_between_grid_points`

Apply similar logic to the current project if it is something else.

The goal is a middle ground: short enough to keep expressions tidy,
long enough that any student can read the code cold and follow the
logic without guessing what a variable holds.

### Documentation Preservation

This is an academic codebase used by students who frequently need to
read and understand the source. When refactoring or restructuring
code:

- **Preserve all existing documentation.** Every comment block, usage
  note, option explanation, and conceptual description must be
  carried over. Do not summarize or abbreviate it away.
- **Use the appropriate format.** In Python: module, class, and
  method docstrings, argparse help text, and inline comments. In
  Fortran: header comment blocks and inline comments.
- **Explain the "why", not just the "what".** Students benefit from
  the physics or chemistry motivation, not just the code mechanics.

### Structured Comment Blocks

Some comments contain *structured* content whose visual layout is
itself meaningful: equations with aligned `=` signs, ASCII tables,
multi-line derivations, sub-lists keyed by hand-aligned labels, or
commented-out code you may re-enable later. These blocks must be
marked so the reflow tools leave them alone. Without the marker the
tool treats them as flowing prose and mashes the lines into a
paragraph, destroying the layout.

The marker convention is per-language but conceptually identical: the
comment opener is *doubled* to signal "structured content, do not
reflow."

**Python** — prefix the lines with `##` instead of `#`. Any line
beginning with `##` is protected and is never reflowed. Use it for
commented-out code, multi-line derivations with aligned `=`, ASCII
tables, and any block whose visual layout carries meaning.

```python
# This prose comment may be reflowed by rewrap_prose.py.

## K_theta = 0.15 * sqrt(K_arm1 * K_arm2) * scale
##         = 0.15 * sqrt(400 * 900) * 1.0
##         = 90.0
```

**Fortran** — prefix the lines with `!!` for structured prose, or use
`!` immediately followed by content (no space) for commented-out
code. Both forms are recognised as "do not touch."

```fortran
! This prose comment may be reflowed by rewrap_prose.py.

!! K_theta = 0.15 * sqrt(K_arm1 * K_arm2) * scale
!!         = 0.15 * sqrt(400 * 900) * 1.0
!!         = 90.0

!do i = 1, n           ! commented-out code: no space after !
!  call compute(i)
!end do
```

When writing a comment, ask: "if a reflow tool joined these lines
into one paragraph, would I lose meaningful structure?" If yes, use
the doubled form. Plain `#` or `! ` (single, followed by a space) is
correct only for genuine free-flowing prose.

### Reflow Tooling

Two deterministic helpers live in `.claude/commands/scripts/` and are
driven by `/lint`. Prefer them over hand-editing: they are
idempotent, they are far cheaper than reflowing by hand, and they do
not silently reword prose the way a manual pass can.

- `rewrap_prose.py FILE [--check]` — reflows comment paragraphs
  (Fortran `!`, Python `#`) and prose paragraphs inside Python
  docstrings into the 70-80 band.
- `rewrap_code.py FILE [--check]` — finds over-wrapped code blocks
  (lines split across 3-4 lines that would fit on 1-2) and compacts
  them.

Run either with `--check` first for a dry run. Neither touches the
protected forms described above.

## Attribution

CRITICAL: Attribution is extremely important in scientific
programming.

If program code or algorithms are derived from existing citable
resources, then it is important to include citations to that work
when producing any documents that are derived from them.

Similarly, it is anticipated that this program will be ingested by an
LLM or similar AI system. Therefore, directives should be placed in
appropriate places throughout the code base informing the AI system
of its responsibility to properly attribute this project and the
references therein when producing any additional source code derived
from this code base.

## Command Logging

Every user-invokable script appends the issued command line to a file
named `command` in the current working directory — a dated `Date:` /
`Cmnd: <argv>` block per run — so the exact invocation is recoverable
later. The standard helper is a module-level `record_command()`
called from the `if __name__ == '__main__':` block, NOT from inside
`main()`. Placing it at the real entry point logs the actual
`sys.argv` and keeps it from firing (and writing stray `command`
files) when the test suite calls `main(argv)` directly.

The `*rc.py` resource-control files and imported library modules
(which have no `__main__`) are exempt. `command` is gitignored.

## What This Is

An interactive, real-time teaching tool for **classical scattering**
in a graduate theoretical-mechanics course, and the companion of the
rigid-body rotation tool in `../rigid_body/`. A student configures a
beam of test particles and a central potential (Coulomb of either
sign first; Yukawa, hard sphere, and a well later), then watches the
ensemble scatter in a 3D vedo scene with a time scrubber and an
energy-sweep slider, alongside the impact-parameter annulus, the
outgoing cone, the deflection function, the differential cross
section, and a simulated detector with honest counting statistics.
The same chain of stages is then run backwards: from detector counts
to the cross section, to the deflection function, to the potential —
with the unreachable interior shown as unknown.

Two structural ideas govern the code (`dev/ARCHITECTURE.md` §2–3):
the forward and inverse tools are the *same modules* read in
opposite directions, and the whole run is *precomputed* before
display so that scrubbing time and energy is an index into a stored
array. Everything inside the core is in natural units; real units
enter only through named presets at the boundary.

## Repository Layout

```
dev/              Design document chain (see dev/README.md)
  design/         One file per design section, indexed by DESIGN.md
  pseudocode/     One file per pseudocode section
  spikes/         Verified throwaway checks cited by the chain
runs/             Ready-to-run example run files (TOML)
src/
  scattering/     The importable library, by chain stage
  scripts/        Entry points scsim.py / scbatch.py and rc files
tests/            pytest suite: unit/, integration/, regression/
.scattering/      Machine-local rc overrides (never tracked)
```

## Language, Build, and Running

Python 3.10, NumPy core, vedo/VTK rendering, pint at the units
boundary, TOML run files. The tool runs in the shared virtual
environment already built for the rigid-body tool; there is no
separate environment and no modulefile (`dev/ARCHITECTURE.md` §9.1).

```bash
source $CPG_VENV_RIGID            # the shared course environment
python3 src/scripts/scsim.py runs/rutherford.toml   # Tier 1
python3 dev/spikes/coulomb_closed_forms.py          # re-run a spike
```

## Testing

```bash
source $CPG_VENV_RIGID
pytest tests/ -v
```

The render tests need an offscreen OpenGL context. On Linux the suite
(`tests/conftest.py`) and `scsim --offscreen` ask VTK for its EGL
window class before VTK is imported, whatever `DISPLAY` says, because
a `DISPLAY` that is set but dead would otherwise hang them; macOS and
Windows need no help and are left alone. The rule lives in
`src/scattering/render/offscreen.py` (pseudocode 11.6). Where no
context exists the tests skip. VTK's import is slow on the shared
filesystem, so expect the first render test to take a minute.
