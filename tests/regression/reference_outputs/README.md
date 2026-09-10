# Reference Outputs

Frozen results that the regression tests compare against.

Regenerating a file here asserts that the new answer is the correct
one. Do it deliberately: in its own commit, with the reason in the
message, and never folded into an unrelated change. A reference
quietly updated alongside the change that altered it records nothing.

Keep each file small enough to read and to diff. When a result is
genuinely large, store a checksum or a reduced summary (a few
moments, a norm, a handful of sampled values) rather than the whole
array, and say in the test what the reduction is and why it is
sufficient to catch the failure you care about.
