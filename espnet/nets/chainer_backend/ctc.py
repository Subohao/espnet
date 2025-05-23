"""Chainer CTC module."""

import logging

import chainer
import chainer.functions as F
import chainer.links as L
import numpy as np


class CTC(chainer.Chain):
    """Chainer implementation of ctc layer.

    Args:
        odim (int): The output dimension.
        eprojs (int | None): Dimension of input vectors from encoder.
        dropout_rate (float): Dropout rate.

    """

    def __init__(self, odim, eprojs, dropout_rate):
        """Initialize CTC class."""
        super(CTC, self).__init__()
        self.dropout_rate = dropout_rate
        self.loss = None

        with self.init_scope():
            self.ctc_lo = L.Linear(eprojs, odim)

    def __call__(self, hs, ys):
        """Compute CTC forward.

        Args:
            hs (list of chainer.Variable | N-dimension array):
                Input variable from encoder.
            ys (list of chainer.Variable | N-dimension array):
                Input variable of decoder.

        Returns:
            chainer.Variable: A variable holding a scalar value of the CTC loss.

        """
        self.loss = None
        ilens = [x.shape[0] for x in hs]
        olens = [x.shape[0] for x in ys]

        # zero padding for hs
        y_hat = self.ctc_lo(
            F.dropout(F.pad_sequence(hs), ratio=self.dropout_rate), n_batch_axes=2
        )
        y_hat = F.separate(y_hat, axis=1)  # ilen list of batch x hdim

        # zero padding for ys
        y_true = F.pad_sequence(ys, padding=-1)  # batch x olen

        # get length info
        input_length = chainer.Variable(self.xp.array(ilens, dtype=np.int32))
        label_length = chainer.Variable(self.xp.array(olens, dtype=np.int32))
        logging.info(
            self.__class__.__name__ + " input lengths:  " + str(input_length.data)
        )
        logging.info(
            self.__class__.__name__ + " output lengths: " + str(label_length.data)
        )

        # get ctc loss
        self.loss = F.connectionist_temporal_classification(
            y_hat, y_true, 0, input_length, label_length
        )
        logging.info("ctc loss:" + str(self.loss.data))

        return self.loss

    def log_softmax(self, hs):
        """Compute Log_softmax of frame activations.

        Args:
            hs (list of chainer.Variable | N-dimension array):
                Input variable from encoder.

        Returns:
            chainer.Variable: A n-dimension float array.

        """
        y_hat = self.ctc_lo(F.pad_sequence(hs), n_batch_axes=2)
        return F.log_softmax(y_hat.reshape(-1, y_hat.shape[-1])).reshape(y_hat.shape)


def ctc_for(args, odim):
    """Return the CTC layer corresponding to the args.

    Args:
        args (Namespace): The program arguments.
        odim (int): The output dimension.

    Returns:
        The CTC module.

    """
    ctc_type = args.ctc_type
    if ctc_type == "builtin":
        logging.info("Using chainer CTC implementation")
        ctc = CTC(odim, args.eprojs, args.dropout_rate)
    else:
        raise ValueError('ctc_type must be "builtin": {}'.format(ctc_type))
    return ctc
