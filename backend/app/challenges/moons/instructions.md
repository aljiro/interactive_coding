Train a binary classifier on the public **two-moons** training set and submit probabilities
for two public input sets:

| dataset | file | purpose |
|---|---|---|
| `test` | `test_features.csv` (1000 rows) | hidden-label evaluation → your score |
| `grid` | `visualization_grid.csv` (100 × 100 = 10 000 rows) | reconstructs your decision surface on the projector |

The **primary score is accuracy on the hidden test labels** (threshold 0.5).
Log loss and Brier score are reported as secondary metrics.

## Files

* `train.csv` — `id,x1,x2,label` (600 points, label ∈ {0, 1})
* `test_features.csv` — `id,x1,x2` (labels are hidden)
* `visualization_grid.csv` — `id,x1,x2` dense grid over x₁ ∈ [−1.75, 2.75], x₂ ∈ [−1.25, 1.75]

Data is generated with `sklearn.datasets.make_moons(noise=0.22)` using fixed seeds
(train `random_state=1`, test `random_state=2`). The same files are committed in the
repository under `examples/data/`, which is what the starter notebook downloads in Colab.
