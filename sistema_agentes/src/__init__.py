from contextlib import AsyncExitStack

_global_exit_stack: AsyncExitStack = None
