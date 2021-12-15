__author__ = 'GCassani'

"""Function to estimate cue-outcome associations given a corpus"""

import os
import json
import numpy as np
from time import strftime
#from cues_outcomes import get_cues_and_outcomes

def get_cues_and_outcomes(input_file):

    """
    :param input_file:      a string indicating the path to the corpus to be considered: it is assumed to be a .json
                            file consisting of two lists of lists: the first encodes learning events into their
                            consistuent phonetic cues, the second encodes the same learning events into their meaning
                            units. Each learning event is a list nested in the two main lists.
                            outcomes; each of the two may consists of multiple, comma-separated strings
    :return cue2ids:        a dictionary mapping each of the strings found in the cues fields to a numerical index
    :return outcome2ids:    a dictionary mapping each of the strings found in the outcomes fields to a numerical index
    """

    outcomes = set()
    cues = set()

    corpus = json.load(open(input_file, 'r+'))

    for i in range(len(corpus[0])):
        trial_cues = set(corpus[0][i])
        cues.update(trial_cues)
        trial_outcomes = set(corpus[1][i])
        outcomes.update(trial_outcomes)

    cues2ids = {k: idx for idx, k in enumerate(sorted(cues))}
    outcomes2ids = {k: idx for idx, k in enumerate(sorted(outcomes))}

    return cues2ids, outcomes2ids

def compute_activations(input_file, output_files, alpha, beta, lam, indices):

    """
    :param input_file:          the path to a a .json file consisting of two lists of lists, the first containing
                                phonetic cues and the second containing outcome meanings; each list contains as many
                                lists as there are learning events in the input corpus (be them full utterances, single
                                words, or any intermediate representation derived from transcribed Child-directed
                                speech). The first list from the list of cue representations matches the first list from
                                the list of meaning representations, both encoding the two layers of the first learning
                                event in the corpus
    :param output_files:        a dictionary mapping time indices indicating the percentage of the input corpus at
                                which the cue-outcome association matrix estimated up to that point needs to be written
                                to file to the file paths where each matrix has to be saved
    :param alpha:               cue salience. For simplicity, we assume that every cue has the same salience, so
                                changing the value of this parameter does not affect the relative strength of
                                cue-outcome associations but only their absolute magnitude.
    :param beta:                learning rate. Again, we make the simplifying assumption that our simulated learners are
                                equally affected by positive and negative feedback. Changing the beta value can have a
                                significant impact on learning outcome, but 0.1 is a standard choice for this model.
    :param lam:                 maximum amount of association that an outcome can receive from all the cues. It simply
                                acts as a scaling factor, so changing its value has the same effects of changing alpha.
    :param indices:             a list of numbers indicating when to store the matrix of associations to file. The
                                numbers indicate percentages of the input corpus.
    """

    folder = os.path.dirname(input_file)
    cue_indices = os.path.join(folder, 'cueIDs.json')
    outcome_indices = os.path.join(folder, 'outcomeIDs.json')

    if os.path.exists(cue_indices) and os.path.exists(outcome_indices):
        cues2ids = json.load(open(cue_indices, 'r'))
        outcomes2ids = json.load(open(outcome_indices, 'r'))
        #print("length of cues: ", len(cues2ids))
        #print("length of outcomes: ", len(outcomes2ids))
    else:
        # get two dictionaries mapping each cue and each outcome from the input corpus to a unique numerical index
        cues2ids, outcomes2ids = get_cues_and_outcomes(input_file)
        #print("length of cues: ", len(cues2ids))
        #print("length of outcomes: ", len(outcomes2ids))
        json.dump(cues2ids, open(cue_indices, 'w'))
        json.dump(outcomes2ids, open(outcome_indices, 'w'))

    print()
    print(strftime("%Y-%m-%d %H:%M:%S") + ": number of cues and outcomes in the input corpus estimated.")
    print()
    
    
    # create an empty matrix with as many rows as there are cues and as many columns as there are outcomes in
    # input corpus. The indices extracted before will point to a row for cues and to a column for outcomes
    weight_matrix = np.zeros((len(cues2ids), len(outcomes2ids)))
    print("shape of matrix: ", weight_matrix.shape)

    # compute the learning rate once and for all, since alpha doesn't change and beta is constant for all cues
    learning_rate = alpha * beta

    print(strftime("%Y-%m-%d %H:%M:%S") + ": started estimating the cue-outcome associations.")

    corpus = json.load(open(input_file, 'r+'))
    # get the total number of learning trials and the line indexes corresponding to each 5% of the corpus to
    # print the advance in processing the input corpus each time an additional 5% of the learning trials is
    # processed
    total_utterances = len(corpus[0])
    check_points = {int(np.floor(total_utterances / 100 * n)): n for n in indices}

    for i in range(len(corpus[0])):
        # get the cues and outcomes in the learning trial
        trial_cues = list(corpus[0][i])
        trial_outcomes = set(corpus[1][i])
        #print("trial cues: ", trial_cues)
        #print("trial outcomes: ", trial_outcomes)

        # Create a masking vector for outcomes: the vector contains 0s for all outcomes that don't occur in the
        # learning trial and the lambda value for all outcomes that don't.
        outcome_mask = np.zeros(len(outcomes2ids))
        for outcome in trial_outcomes:
            outcome_mask[outcomes2ids[outcome]] = lam
        #print("outcome_mask: ", outcome_mask)

        # create a masking vector for the cues: this vector contains as many elements as there are cues in the
        # learning trial. If a cue occurs more than once, its corresponding index will appear more than once
        cue_mask = []
        for cue in trial_cues:
            cue_mask.append(cues2ids[cue])
        #print("cue_mask: ", cue_mask)

        # compute the total activation for each outcome given the cues in the current learning trial. In order
        # to select the cues that are present in the learning trial - and only those - the cue masking vector is
        # used: it subsets the weight matrix using the indices appended to it, and a row is considered as many
        # times as its corresponding index occurs in the current trial. Then, a sum is performed column-wise
        # returning the total activation for all outcomes. The total activation for unknown outcomes, those that
        # are yet to be experienced, will be 0.
        total_v = np.sum(weight_matrix[cue_mask], axis=0)
        #print("total activation: ", total_v)

        """
        exceeding_ids = np.argwhere(total_v > lam)
        exceeding_lam = total_v[total_v > lam]
        if total_v[total_v > lam].any():
            print(strftime("%Y-%m-%d %H:%M:%S") + ": Something went wrong with utterance number %d:" % i)
            print('outcomes for which activation over cues exceeds lambda: ', exceeding_ids)
            print('activation for outcomes with activation higher than lambda: ', exceeding_lam)
            print(trial_cues, trial_outcomes)
        """

        # compute the change in activation for each outcome using the outcome masking vector (that has a value
        # of 0 in correspondence of all absent outcomes and a value of lambda in correspondence of all present
        # outcomes). Given that yet to be experienced outcomes have a total activation of 0 and a lambda value
        # of 0, no change in association happens for cue-outcome associations involving these outcomes. On the
        # contrary, known but not present outcomes have a lambda value of 0 (in the outcome mask vector) but a
        # total activation higher or lower, resulting in a change of association.
        delta_a = (outcome_mask - total_v) * learning_rate

        # sum the vector of changes in association to the weight matrix: each value in delta_a is summed to all
        # values in the corresponding column of the weight_matrix indicated by cue_mask
        weight_matrix[cue_mask] += delta_a

        # print to console the progress made by the function
        if i+1 in check_points:
            print(strftime("%Y-%m-%d %H:%M:%S") + ": %d%% of the input corpus has been processed."
                  % check_points[i+1])

            if os.path.exists(output_files[check_points[i+1]]):
                print("The file %s already exists." % output_files[check_points[i+1]])
            else:
                np.save(output_files[check_points[i+1]], weight_matrix)
