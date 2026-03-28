"""top_k.py — position-weighted retrieval evaluator for the rag_pipeline experiment.

The runner discovers this file and loads the ``top_k`` attribute (matching the
filename stem) as an evaluator for the experiment.
"""

from evalwire.evaluators import make_top_k_evaluator

# Expose as module-level callable so the runner can load it by name.
top_k = make_top_k_evaluator(K=5)
