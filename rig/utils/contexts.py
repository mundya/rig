'Utilities for building contextual functions.\n\nThe MachineController has a lot of functions which take the same arguments,\nmany of which are contextual.  For example, when performing multiple operations\non a given chip::\n\n    controller.sdram_alloc(1000, 1, x=3, y=2)\n    controller.sdram_alloc(1000, 2, x=3, y=2)\n\nAvoiding respecifying these arguments every time\nwill lead to cleaner and clearer code.  For example:\n\n    with controller(app_id=32):\n        with controller(x=1, y=1):\n            controller.do_something(...)\n\n        with controller(x=2, y=2):\n            controller.do_something(...)\n\nIs, in many cases, arguably clearer and less prone to silly mistakes than:\n\n    controller.do_something(x=1, y=1, app_id=32)\n    controller.do_something(x=2, y=2, app_id=32)\n\nThough this form is still useful and should be allowed.\n\nThis module provides decorators for functions so that they can use contextual\narguments and a mixin for classes that provides a `get_new_context` method\nwhich could be mapped to `__call__` to produce and use concepts as in the\nprevious example.\n'
import collections
import inspect
import functools
import sentinel
from six import iteritems
Required=sentinel.create('Required')
'Allow specifying keyword arguments as required, i.e., they must be satisfied\nby either the context OR by the caller.\n\nThis is useful when a method has optional parameters and contextual arguments::\n\n    @ContextMixin.use_contextual_arguments\n    def sdram_alloc(self, size, tag=0, x=Required, y=Required):\n        # ...\n'
class ContextMixin(object):
 'A mix-in which provides a context stack and allows querying of the stack\n    to form keyword arguments.\n    '
 def __init__(self,initial_context={}):'Create a context stack for this object.\n\n        Parameters\n        ----------\n        initial_context : {kwarg: value}\n            An initial set of contextual arguments mapping keyword to value.\n        ';self.__context_stack=collections.deque();self.__context_stack.append(Context(initial_context))
 def get_new_context(self,**kwargs):'Create a new context with the given keyword arguments.';return Context(kwargs,self.__context_stack)
 def update_current_context(self,**context_args):'Update the current context to contain new arguments.';self.__context_stack[-1].update(context_args)
 def get_context_arguments(self):
  'Return a dictionary containing the current context arguments.';cargs={}
  for context in self.__context_stack:cargs.update(context.context_arguments)
  return cargs
 @staticmethod
 def use_contextual_arguments(f):
  'Decorator which modifies a function so that it is passed arguments\n        from the call or from the current context.\n        ';arg_names,_,_,defaults=inspect.getargspec(f);kwargs=arg_names[-len(defaults):];default_call=dict(zip(kwargs,defaults))
  @functools.wraps(f)
  def f_(*args,**kwargs):
   self=args[0];kwargs.update(dict(zip(arg_names[1:],args[1:])));cargs=self.get_context_arguments();calls={k:cargs.get(k,v) for (k,v) in iteritems(default_call)};calls={k:kwargs.get(k,v) for (k,v) in iteritems(calls)}
   for k,v in iteritems(calls):
    if v is Required:raise TypeError('{!s}: missing argument {}'.format(f.__name__,k))
   kwargs.update(calls);return f(self,**kwargs)
  return f_
 @staticmethod
 def use_named_contextual_arguments(**named_arguments):
  'Decorator which modifies a function such that it is passed arguments\n        given by the call and named arguments from the call or from the\n        context.\n\n        Parameters\n        ----------\n        **named_arguments : {name: default, ...}\n            All named arguments are given along with their default value.\n        '
  def decorator(f):
   @functools.wraps(f)
   def f_(self,*args,**kwargs):
    new_kwargs=named_arguments.copy();cargs=self.get_context_arguments()
    for name,val in iteritems(cargs):
     if name in new_kwargs:new_kwargs[name]=val
    new_kwargs.update(kwargs)
    for k,v in iteritems(new_kwargs):
     if v is Required:raise TypeError('{!s}: missing argument {}'.format(f.__name__,k))
    return f(self,*args,**new_kwargs)
   return f_
  return decorator
class Context(object):
 'A context object that stores arguments that may be passed to\n    functions.\n    '
 def __init__(self,context_arguments,stack=None):'Create a new context object that can be added to a stack.\n\n        Parameters\n        ----------\n        context_arguments : {kwarg: value}\n            A dict of contextual arguments mapping keyword to value.\n        stack : :py:class:`deque`\n            Context stack to which this context will append itself when\n            entered.\n        ';self.context_arguments=dict(context_arguments);self.stack=stack
 def update(self,updates):'Update the arguments contained within this context.';self.context_arguments.update(updates)
 def __enter__(self):self.stack.append(self)
 def __exit__(self,exception_type,exception_value,traceback):removed=self.stack.pop();assert removed is self
