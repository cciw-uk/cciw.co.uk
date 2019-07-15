def partition(pred, iterable):
    trues = []
    falses = []
    for i in iterable:
        if pred(i):
            trues.append(i)
        else:
            falses.append(i)
    return trues, falses
