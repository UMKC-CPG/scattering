# The `dev/` Directory

Everything here is development material. Only some of it is part of
the design chain, and the distinction matters: a chain document
*specifies* behavior and is binding on the level below it, while
everything else merely *records* something. Confusing the two is how
a project ends up with code justified by a note nobody ratified.

## The chain

| Path | Level | Question it answers |
| --- | --- | --- |
| `VISION.md` | 1 | Why does this project exist? |
| `ARCHITECTURE.md` | 2 | How is it organized? |
| `DESIGN.md` + `design/` | 3 | How do the algorithms work? |
| `PSEUDOCODE.md` + `pseudocode/` | 4 | What are the steps, precisely? |
| `../src/` | 5 | The implementation. |

`DESIGN.md` and `PSEUDOCODE.md` are indexes; the numbered sections
live in `design/NN-topic.md` and `pseudocode/NN-topic.md`. Add a
section file and its index row in the same edit.

## Not the chain

`TODO.md` tracks tasks by level. It is a work queue, not a
specification — see the "A detailed TODO entry is not pseudocode"
warning in `../CLAUDE.md`.

`notes/` holds dated working notes: discussion write-ups, state-of-
the-project snapshots, recipes, and anything else that captures
thinking in progress. Name files `topic.md` or `topic-YYYY-MM-DD.md`.
A note is never binding. When something in a note becomes a decision,
promote it into the chain and leave the note as provenance.

`figures/` holds diagrams and their editable sources (`.png` next to
the `.pptx` or `.svg` that produced it). Chain documents may embed
them; the figure itself specifies nothing.

## Artifacts to add when a project needs them

These are not shipped as stubs, because a project that does not need
one is better off without an empty file inviting it to be filled.
Each has been earned on an earlier project, so create it from the
pattern described here rather than reinventing the category.

**`spikes/`** — present in this project. Throwaway experiments kept
because their *results* are cited in the chain. A spike is not
production code and is not held to the architecture: it exists to answer
one question, and it stays in the repository only so the answer can be
re-checked when the hardware, libraries, or problem size change. Give
the directory a `README.md` with one entry per spike recording: the
question it answered, the answer, where in the chain that answer is now
cited, any trap it guards against, and the exact command to re-run it.

Spikes pay for themselves. On an earlier project one caught a
remembered physical constant that was wrong by exactly a factor of
two, before it reached DESIGN, the code, and the code's own tests.

**`PRIOR_ART.md`** — a cross-cutting record of existing work, inside
or outside the group, that overlaps this project, so ARCHITECTURE and
DESIGN can point at already-built assets instead of re-deriving them.
Each entry should say plainly what is *usable now*, what is
*design-only*, and what to *leave behind*.

**Campaign ledgers** — a long, bounded hunt through the whole code
base for one class of problem gets its own ledger: `DEBUG.md` for
correctness bugs, `PERFORMANCE.md` for time and memory, `SECURITY.md`
for what a hostile input could make the program do. Give each a
Purpose, a Status, a Methodology, and a findings list ranked by that
campaign's own severity scale.

Keep them separate rather than merging them. A bug ledger ranks
findings by what the program does wrong on honest input; a security
ledger ranks them by what an adversary can force on dishonest input;
a performance ledger by cost. A bug that never fires on a real deck
can still be a critical vulnerability, and a glaring numerical bug
can have no security consequence at all. One severity scale cannot
serve two unrelated questions.

**`tools/`** — small analysis programs used on the project but not
shipped with it: output differs, timing harnesses, warning-manifest
checkers.

**`env/`** — captured environment specifications (conda YAML, module
lists) recording what the project was actually built and run against.

**A staging document** — when a decision must survive between
sessions but is not yet ratified (a table of candidate parameter
values with their literature sources, say), give it its own file and
mark its status in the header. When it is ratified, distill it into
the chain and keep the file as the provenance record for *why* each
value was chosen.

## The preamble every non-chain document needs

Any document added here that is not a chain level must say so in its
header, so no later reader mistakes it for one:

> **Document hierarchy:** this is a tracking artifact, not a sixth
> level of the chain (VISION → ARCHITECTURE → DESIGN → PSEUDOCODE →
> code). It sits alongside those documents and references them where
> a finding touches a design decision, but it does not itself specify
> behavior. When something here reveals a flaw at a chain level, that
> flaw is propagated up the chain in the normal way, and the entry
> here is left as a pointer.
