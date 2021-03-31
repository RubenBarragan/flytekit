from typing import Optional

from flytekit.common.exceptions import user as _user_exceptions
from flytekit.common.mixins import artifact as _artifact_mixin
from flytekit.engines.flyte import engine as _flyte_engine
from flytekit.models.admin import task_execution as _task_execution_model
from flytekit.models.core import execution as _execution_models


class FlyteTaskExecution(_task_execution_model.TaskExecution, _artifact_mixin.ExecutionArtifact):
    def __init__(self, *args, **kwargs):
        super(FlyteTaskExecution, self).__init__(*args, **kwargs)
        self._inputs = None
        self._outputs = None

    @property
    def is_complete(self) -> bool:
        """Whether or not the execution is complete."""
        return self.closure.phase in {
            _execution_models.TaskExecutionPhase.ABORTED,
            _execution_models.TaskExecutionPhase.FAILED,
            _execution_models.TaskExecutionPhase.SUCCEEDED,
        }

    @property
    def inputs(self):
        # TODO
        pass

    @property
    def outputs(self):
        # TODO
        pass

    @property
    def error(self) -> Optional[_execution_models.ExecutionError]:
        """
        If execution is in progress, raise an exception. Otherwise, return None if no error was present upon
        reaching completion.
        """
        if not self.is_complete:
            raise _user_exceptions.FlyteAssertion(
                "Please what until the task execution has completed before requesting error information."
            )
        return self.closure.error

    def get_child_executions(self, filters=None):
        from flytekit.control_plane import nodes as _nodes

        if not self.is_parent:
            raise _user_exceptions.FlyteAssertion("Only task executions marked with 'is_parent' have child executions.")
        client = _flyte_engine.get_client()
        models = {
            v.id.node_id: v
            for v in _iterate_node_executions(client, task_execution_identifier=self.id, filters=filters)
        }

        return {k: _nodes.FlyteNodeExecution.promote_from_model(v) for k, v in _six.iteritems(models)}

    @classmethod
    def promote_from_model(cls, base_model: _task_execution_model.TaskExecution) -> "FlyteTaskExecution":
        return cls(
            closure=base_model.closure,
            id=base_model.id,
            input_uri=base_model.input_uri,
            is_parent=base_model.is_parent,
        )

    def sync(self):
        """
        Syncs the state of the underlying execution artifact with the state observed by the platform.
        """
        self._sync_closure()

    def _sync_closure(self):
        """
        Syncs the closure of the underlying execution artifact with the state observed by the platform.
        """
        self._closure = _flyte_engine.get_client().get_task_execution(self.id).closure
