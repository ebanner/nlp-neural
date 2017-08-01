import numpy as np
import pandas as pd


def valid_pairs_generator(cdnos, nb_sample, cdno_matching, seed, full):
    """Generator for generating batches of source_idxs to valid corrupt_idxs. The
    definition of "valid" is determined by the value of `cdno_matching`

    Parameters
    ----------
    cdnos : mapping from study indexes to their cdno
    nb_sample : number of studies to evaluate
    cdno_matching : valid_idxs[i] == source_idxs[i] if True else valid_idxs[i] only
    has to have the same cdno as source_idxs[i]
    seed : int to use for the random seed
    full : return batches of the form [range(nb_cdno)] -> [valid_studies]

    """
    random = np.random.RandomState(seed) if seed else np.random # for reproducibility!
    nb_cdno, cdno_set = len(cdnos), set(np.unique(cdnos))

    # dict to sample studies with same cdno
    cdno2valid_study_idxs = {}
    for cdno in cdno_set:
        cdno_idxs = set(np.argwhere(cdnos == cdno).flatten())
        cdno2valid_study_idxs[cdno] = cdno_idxs

    while True:
        # sample study indices
        study_idxs = random.choice(nb_cdno, size=nb_sample, replace=False) if not full else np.array(range(nb_sample))
        valid_idxs = study_idxs.copy() # create valid indices
        if not cdno_matching:
            # find study idxs in the same study
            for i, study_idx in enumerate(study_idxs):
                try:
                    cdno = cdnos[study_idx]
                    valid_study_idxs = cdno2valid_study_idxs[cdno]
                    valid_study_idxs = valid_study_idxs - set([study_idx]) # remove study iteself from consideration
                    valid_study_idx = random.choice(list(valid_study_idxs))
                    valid_idxs[i] = valid_study_idx
                except ValueError:
                    print study_idx
                    print cdno2valid_study_idxs[cdno]
                
        yield study_idxs, valid_idxs

def corrupt_pairs_generator(cdnos, nb_sample, seed, full):
    """Generator for generating batches of source_idxs to valid corrupt_idxs
    
    Parameters
    ----------
    cdnos : list of cdnos which identify studies
    nb_sample : number of pairs to generate
    seed : random seed integer value
    full : return batches of the form [range(nb_cdno)] -> [corrupt_studies]
    
    """
    random = np.random.RandomState(seed) if seed else np.random # for reproducibility!
    nb_cdno, cdno_set = len(cdnos), set(np.unique(cdnos))

    # dict to sample studies with same cdno
    all_cdno_idxs = set(np.arange(nb_cdno))
    cdno2corrupt_study_idxs = {}
    for cdno in cdno_set:
        cdno_idxs = set(np.argwhere(cdnos == cdno).flatten())
        cdno2corrupt_study_idxs[cdno] = list(all_cdno_idxs - cdno_idxs)

    while True:
        # sample study indices
        study_idxs = random.choice(nb_cdno, size=nb_sample, replace=False) if not full else np.array(range(nb_sample))
        corrupt_idxs = np.zeros_like(study_idxs) # create corrupt idxs
        for i, study_idx in enumerate(study_idxs):
            cdno = cdnos[study_idx]
            corrupt_study_idxs = cdno2corrupt_study_idxs[cdno]
            corrupt_study_idx = random.choice(corrupt_study_idxs)
            corrupt_idxs[i] = corrupt_study_idx

        yield study_idxs, corrupt_idxs

def study_target_generator(X_source, X_target, cdnos, exp_group, exp_id, nb_sample=128,
        seed=None, full=False, neg_nb=-1, cdno_matching=True, pos_ratio=.1):
    """Wrapper generator around valid_pairs_generator() and
    corrupt_pairs_generator() for yielding batches of ([study, target], y)
    pairs.

    Parameters
    ----------
    X_source : vectorized abstracts
    X_target : either vectorized abstracts or vectorized summaries
    cdnos : corresponding cdno list
    seed : the random seed to use
    nb_sample : number of samples to return
    neg_nb : number to use for negative examples (use 0 for binary CE and -1 for hinge loss)
    cdno_matching : yield same indexes for positive examples if `True` else yield
    indexes just in the same study if `False`
    pos_ratio : ratio of positive examples to total examples in a batch

    The first half of pairs are of the form ([study, corresponding-summary],  1)
    and second half are of the form ([study, summary-from-different-review], neg_nb).

    """
    nb_sample = nb_sample*2 if full else nb_sample
    nb_valid = int(nb_sample * pos_ratio)
    nb_neg = nb_sample - nb_valid

    # construct y
    y = np.full(shape=[nb_sample, 1], fill_value=neg_nb, dtype=np.int)
    y[:nb_valid, 0] = 1 # first half of samples are good always

    # generators
    valid_source_target_batch = valid_pairs_generator(cdnos, nb_valid, cdno_matching, seed, full)
    corrupt_source_target_batch = corrupt_pairs_generator(cdnos, nb_neg, seed, full)

    while True:
        source_idxs, valid_target_idxs = next(valid_source_target_batch)
        more_source_idxs, corrupt_target_idxs = next(corrupt_source_target_batch)

        source_idxs = np.concatenate([source_idxs, more_source_idxs])
        target_idxs = np.concatenate([valid_target_idxs, corrupt_target_idxs])

        yield [X_source[source_idxs], X_target[target_idxs]], y
