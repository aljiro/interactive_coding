## Prediction CSV

Upload one CSV with **every** `test` id and **every** `grid` id:

```csv
dataset,id,probability
test,0,0.021
test,1,0.912
...
grid,0,0.001
...
```

`probability` is the probability of class 1 and must be a finite number in [0, 1].
Missing, duplicate or unknown ids are rejected with a message telling you what is wrong.
`sample_predictions.csv` shows the exact format (a useless constant-0.5 submission).
