## Python bundle (ZIP)

Upload `submission.zip` containing `submission.py` with:

```python
def predict(X):
    """X: numpy.ndarray (N, 2) -> numpy.ndarray (N,) of class-1 probabilities."""
```

plus any files it loads (e.g. `weights.pt`). It runs in an isolated container
(no network, 1 CPU, 512 MB, 30 s) with `numpy`, `scipy`, `scikit-learn` and `torch` available.
Load files relative to `__file__` and keep inference fast. `submission_template.py` is a skeleton.
