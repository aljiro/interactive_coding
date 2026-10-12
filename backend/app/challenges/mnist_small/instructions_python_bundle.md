## Python bundle (ZIP)

Upload `submission.zip` containing `submission.py` with:

```python
def predict(X):
    """X: numpy.ndarray (N, 784) of raw pixels in 0..255
    -> numpy.ndarray (N, 10) of class probabilities (rows sum to 1)."""
```

plus any files it loads (e.g. `weights.pt`). It runs in an isolated container
(no network, 1 CPU, 512 MB, 30 s) with `numpy`, `scipy`, `scikit-learn` and `torch` available.

`X` arrives **exactly as in `mnist_train.csv`** (raw 0…255). Whatever preprocessing you use
for training must be applied inside `predict` too; the notebook keeps it in one function
for that reason. Return softmax probabilities, not logits. Load files relative to `__file__`
and keep inference fast. `submission_template.py` is a skeleton.
