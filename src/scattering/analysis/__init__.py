"""Is it right? The conservation monitor and the error budget.

Governed by pseudocode section 9 and design section 9. Three kinds of error --
numerical, statistical, and assumption -- are measured separately and shown side
by side, never combined; a structural test enforces that no expression mixes
fields across the three columns. These are runtime components (the panel reads
them), not test helpers.
"""

from scattering.analysis.conservation_monitor import (residual_maxima,
                                                      residual_series)
from scattering.analysis.error_budget import (AssumptionColumn, ErrorBudget,
    NumericalColumn, StatisticalColumn, TrackedSeries, build_error_budget)

__all__ = ['residual_maxima', 'residual_series', 'AssumptionColumn',
           'ErrorBudget', 'NumericalColumn', 'StatisticalColumn',
           'TrackedSeries', 'build_error_budget']
