# Copyright (c) Facebook, Inc. and its affiliates.

from mmf.trainers.callbacks.base import Callback
from mmf.utils.distributed import broadcast_scalar, is_master, is_xla
from mmf.utils.early_stopping import EarlyStopping

try:
    import torch_xla.core.xla_model as xm
except ImportError:
    xm = None

class EarlyStoppingCallback(Callback):
    """Callback for Early Stopping mechanism and checks if it training
    should continue or stop.
    """

    def __init__(self, config, trainer):
        """
        Attr:
            config(mmf_typings.DictConfig): Config for the callback
            trainer(Type[BaseTrainer]): Trainer object
        """
        super().__init__(config, trainer)

        early_stop_criteria = self.training_config.early_stop.criteria
        early_stop_minimize = self.training_config.early_stop.minimize
        early_stop_enabled = self.training_config.early_stop.enabled
        early_stop_patience = self.training_config.early_stop.patience
        self.early_stopping = EarlyStopping(
            self.trainer.model,
            self.trainer.checkpoint_callback.checkpoint,
            early_stop_criteria,
            patience=early_stop_patience,
            minimize=early_stop_minimize,
            should_stop=early_stop_enabled,
        )

    def on_validation_end(self, **kwargs):
        stop = self.early_stopping(
            self.trainer.num_updates, self.trainer.current_iteration, kwargs["meter"]
        )
        if is_xla(): 
            stop = stop and is_master()
            stop = xm.mesh_reduce('early_stop', stop , lambda x: bool(sum(x)))
        else:
            stop = bool(broadcast_scalar(stop, src=0, device=self.trainer.device))
        return stop
