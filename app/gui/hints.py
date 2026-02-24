"""
app/gui/hints.py — User-facing hint strings
============================================
Centralises all tooltip and descriptive subtitle text so they can be
updated without touching layout code.
"""

# ---------------------------------------------------------------------------
# Tooltip text — shown on hover over the title label of each content frame
# ---------------------------------------------------------------------------

VERSION_TOOLTIP = (
    "A Version represents a distinct modelling intent or design concept.\n"
    "Each Version can contain multiple Iterations."
)

ITERATION_TOOLTIP = (
    "An Iteration is a specific solver configuration within a Version — defined by solver type and analysis types.\n"
    "Each Iteration can contain multiple Runs."
)

RUN_TOOLTIP = (
    "A Run is a single solver execution within an Iteration.\n"
    "It tracks the input deck, output artifacts, and convergence status."
)

# ---------------------------------------------------------------------------
# Dialog subtitle text — shown below the heading in creation dialogs
# ---------------------------------------------------------------------------

NEW_VERSION_SUBTITLE = (
    "A Version represents a distinct modelling intent or design concept.\n"
    "Use a new Version to capture a fundamentally different approach to the model."
)

NEW_ITERATION_SUBTITLE = (
    "An Iteration is a specific solver configuration within a Version — defined by solver type and analysis types.\n"
    "Use a new Iteration for each distinct solver or analysis setup within the same design intent."
)

NEW_RUN_SUBTITLE = (
    "Registering a run generates the solver deck filename.\n"
    "Copy it from the Iteration view before executing the solver."
)
