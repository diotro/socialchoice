"""
This file holds the complete interface for this package, as everything in here can be imported as
socialchoice.{whatever} instead of socialchoice.{filename}.{whatever}

This allows us to factor out the package into multiple files while keeping a consistent user-facing API.
"""

from ballot import \
    InvalidVoteShapeException, \
    InvalidPairwiseVoteTypeException, \
    BallotBox, \
    PairwiseBallotBox, \
    RankedChoiceBallotBox

from election import Election
