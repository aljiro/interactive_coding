You get **1000 handwritten digits** (100 per class) and a starter notebook whose training
routine is deliberately naive: it barely learns. Your job is **learning engineering**:

1. **Make it train.** Find out why the loss hardly moves and fix the recipe
   (input scaling, activations/initialisation, optimiser, learning rate, batch size, …).
2. **Make it generalise.** With only 1000 examples an MLP memorises the training set
   easily. Close the gap between training accuracy and hidden-test accuracy
   (validation split, early stopping, weight decay, dropout, schedules, augmentation, …).

Submit as often as you like; the projector shows each person's **best** submission.

| dataset | what the server does with it |
|---|---|
| `test` | 5000 hidden-label digits → **your score** (accuracy) |
| `train` | the public 1000 training digits → your *training accuracy* and the train − test gap |

The **primary score is accuracy on the hidden test digits**. Training accuracy, the
generalisation gap and log loss are reported as secondary metrics. The projector plots
training accuracy against hidden-test accuracy: the further a point sits below the
diagonal, the more that model is overfitting.

## Files

* `mnist_train.csv` — `id,label,p0,…,p783`: one row per digit, label ∈ {0,…,9}, 784 **raw**
  pixel values in 0…255 (row-major 28 × 28). The same file is committed in the repository
  under `examples/data/`, which is what the starter notebook downloads in Colab.

The images are a fixed, balanced subset of the standard MNIST training split; the hidden
test digits come from the MNIST test split. Please train only on the 1000 digits provided:
this challenge is about the recipe, not about fetching more data.
