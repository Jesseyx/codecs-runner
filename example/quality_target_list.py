def get_qvbr_quality_list():
    arr = []
    for b in [8800, 5630]:
        for quality in list(range(29,30)):
            arr.append({ 'b': b, 'quality': quality})
    return arr

def get_qvbr2_quality_list():
    arr = []
    for b in [4000, 3000]:
        for quality in list(range(30,32)):
            arr.append({ 'b': b, 'quality': quality})
    return arr

qvbr = get_qvbr_quality_list() # notice: there qvbr and qvbr2 is the task name for search data. if not find special task, default will use for all task.
qvbr2 = get_qvbr2_quality_list()
