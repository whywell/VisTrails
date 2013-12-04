from vistrails.core.utils import bisect, enum


SchemeType = enum(
        'SchemeType',
        ['THREAD', 'LOCAL_PROCESS', 'REMOTE_MACHINE', 'REMOTE_NO_VISTRAILS'])


class ParallelizationScheme(object):
    """A way to execute code remotely.

    This is the base class for all the different way to execute code in
    parallel, for instance in a thread, another process, on a cluster...
    """
    @staticmethod
    def get_gui_widget():
        return None

    def __init__(self, priority, scheme_type, name):
        self.priority = priority
        self.scheme_type = scheme_type
        self.name = name

    def supports(self, thread, process, remote, standalone, systems):
        if not self.enabled():
            return False

        if self.name in systems:
            return systems[self.name]

        if self.scheme_type == SchemeType.THREAD and thread:
            return True
        elif self.scheme_type == SchemeType.LOCAL_PROCESS and process:
            return True
        elif self.scheme_type == SchemeType.REMOTE_MACHINE and remote:
            return True
        elif self.scheme_type == SchemeType.REMOTE_NO_VISTRAILS and standalone:
            return True
        else:
            return False

    def enabled(self):
        return True

    def do_compute(self, module):
        raise NotImplementedError

    def finalize(self):
        pass


class RemoteExecution(object):
    """This defines what a Module supports as execution target.

    It knows how to select, among the currently available schemes, the best
    that the module supports.
    """
    def __init__(self, thread=False, process=False, remote=False,
                 standalone=False, systems={}):
        self.parallelizable = dict(
                thread=thread,
                process=process,
                remote=remote,
                standalone=standalone,
                systems=systems)

    def __or__(self, other):
        o = other.parallelizable
        s = self.parallelizable
        n = {}
        n['thread'] = o['thread'] and s['thread']
        n['process'] = o['process'] and s['process']
        n['remote'] = o['remote'] and s['remote']
        n['standalone'] = o['standalone'] and s['standalone']

        systems = set(s['systems'].iterkeys())
        systems.update(o['systems'].iterkeys())
        sy = {}
        for system in systems:
            s_s = s['systems'].get(system)
            o_s = o['systems'].get(system)
            if s_s is False or o_s is False:
                sy[system] = False
            elif s_s is None or o_s is None:
                pass
            else:
                sy[system] = True
        n['systems'] = sy

        return RemoteExecution(**n)

    def __eq__(self, other):
        return self.parallelizable == other.parallelizable

    def __repr__(self):
        return '<%s at %r: %r>' % (self.__class__.__name__, id(self),
                                   self.parallelizable)
    __str__ = __repr__

    @staticmethod
    def do_compute(module):
        """This method is injected as do_compute in parallelizable modules.

        When the parallelizable() class decorator is used on a class, this
        method is called instead of do_compute. The original arguments to
        parallelizable() will be used to choose a specific scheme.
        """
        supported = module.remote_execution

        # If we're already a remote machine, only use threads
        if Parallelization.is_subprocess:
            supported = RemoteExecution(
                    thread=supported.parallelizable['thread'])

        for priority, scheme in Parallelization._parallelization_schemes:
            if scheme.supports(**supported.parallelizable):
                scheme.do_compute(module)
                return

        # Fallback to classic execution
        module.do_compute()


@apply
class Parallelization(object):
    """Singleton holding all the ParallelizationSchemes.
    """
    def __init__(self):
        self.is_subprocess = False
        self._parallelization_schemes = []

    def set_is_subprocess(self, sub=True):
        """This allows to globally disable remote executions.

        It is useful when we are using VisTrails to execute a pipeline on the
        remote side, to prevent the remote from executing remotely in its turn.
        """
        self.is_subprocess = sub

    def setup_parallelization_schemes(self):
        import parallel_thread
        import parallel_process
        import parallel_ipython

    def register_parallelization_scheme(self, scheme):
        """Registers a ParallelizationScheme to be used by parallelizable().
        """
        priority = scheme.priority
        i = bisect(
                len(self._parallelization_schemes),
                self._parallelization_schemes.__getitem__,
                (priority, scheme),
                comp=lambda a, b: a[0] < b[0])
        self._parallelization_schemes.insert(i, (priority, scheme))

    def finalize_parallelization_schemes(self):
        """Finalize every ParallelizationScheme.
        """
        for priority, scheme in self._parallelization_schemes:
            scheme.finalize()
        self._parallelization_schemes = []

    @property
    def parallelization_schemes(self):
        return [scheme for priority, scheme in self._parallelization_schemes]


###############################################################################

import unittest


class TestRemoteExecution(unittest.TestCase):
    def test_intersection(self):
        self.assertEqual(
                RemoteExecution(thread=True, process=False, remote=True) |
                RemoteExecution(thread=False, process=True, remote=True),
                RemoteExecution(thread=False, process=False, remote=True,
                                standalone=False))

        self.assertEqual(
                RemoteExecution(systems={'one': True, 'two': True}) |
                RemoteExecution(systems={'one': False, 'three': False}),
                RemoteExecution(thread=False, process=False, remote=False,
                                standalone=False,
                                systems={'one': False, 'three': False}))
