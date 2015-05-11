#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2015 by Frank Brehm, Berlin
@summary: All modules for handling LVM stuff
"""

# Standard modules
import os
import re
import logging
import errno
import pipes
import signal

# Third party modules

# Own modules
from pb_base.handler import CommandNotFoundError
from pb_base.handler import PbBaseHandler

from pb_base.handler.lock import PbLockHandler

from pb_blockdev.base import BlockDeviceError

from pb_blockdev.translate import pb_gettext, pb_ngettext

_ = pb_gettext
__ = pb_ngettext

__version__ = '0.1.0'

#LVM_PATH = "/usr/sbin"
LVM_PATH = os.sep + os.path.join('usr', 'sbin')

LOG = logging.getLogger(__name__)

LVMDISKSCAN_BIN_PATH = os.path.join(LVM_PATH, 'lvmdiskscan')
if not os.access(LVMDISKSCAN_BIN_PATH, os.F_OK):
    #LVM_PATH="/sbin"
    LVM_PATH = os.sep + 'sbin'
    LVMDISKSCAN_BIN_PATH = os.path.join(LVM_PATH, 'lvmdiskscan')

LVM_BIN_PATH       = os.path.join(LVM_PATH, 'lvm')
LVDISPLAY_BIN_PATH = os.path.join(LVM_PATH, 'lvdisplay')
LVCREATE_BIN_PATH  = os.path.join(LVM_PATH, 'lvcreate')
LVCHANGE_BIN_PATH  = os.path.join(LVM_PATH, 'lvchange')
LVCONVERT_BIN_PATH = os.path.join(LVM_PATH, 'lvconvert')
LVRENAME_BIN_PATH  = os.path.join(LVM_PATH, 'lvrename')
LVEXTEND_BIN_PATH  = os.path.join(LVM_PATH, 'lvextend')
LVREDUCE_BIN_PATH  = os.path.join(LVM_PATH, 'lvreduce')
LVREMOVE_BIN_PATH  = os.path.join(LVM_PATH, 'lvremove')
PVCREATE_BIN_PATH  = os.path.join(LVM_PATH, 'pvcreate')
PVREMOVE_BIN_PATH  = os.path.join(LVM_PATH, 'pvremove')
PVMOVE_BIN_PATH    = os.path.join(LVM_PATH, 'pvmove')
VGCREATE_BIN_PATH  = os.path.join(LVM_PATH, 'vgcreate')
VGCHANGE_BIN_PATH  = os.path.join(LVM_PATH, 'vgchange')
VGEXTEND_BIN_PATH  = os.path.join(LVM_PATH, 'vgextend')
VGREDUCE_BIN_PATH  = os.path.join(LVM_PATH, 'vgreduce')
VGREMOVE_BIN_PATH  = os.path.join(LVM_PATH, 'vgremove')

DEFAULT_LVM_LOCKFILE = os.sep + os.path.join('var', 'lock', 'lvm', 'global.lock')

DEFAULT_LVM_TIMEOUT = 15


# =============================================================================
class GenericLvmError(BlockDeviceError):
    """Base exception class for all LVM errors"""
    pass


# =============================================================================
class LvmExecError(GenericLvmError):
    """Exception class for errors on executing a LVM command"""
    pass


# =============================================================================
class LvmTimeoutError(LvmExecError, IOError):
    """Special exception class for timeout on execution of a LVM command."""

    # -------------------------------------------------------------------------
    def __init__(self, timeout, cmd):
        """
        Constructor.

        @param timeout: the timout in seconds leading to the error
        @type timeout: float
        @param cmd: the command, which execution lead to a timeout.
        @type cmd: str

        """

        t_o = None
        try:
            t_o = float(timeout)
        except ValueError:
            pass
        self.timeout = t_o

        strerror = _("Timeout on executing %r.") % (cmd)

        if t_o is not None:
            strerror += _(" (timeout after %0.1f secs)") % (t_o)

        super(LvmTimeoutError, self).__init__(errno.ETIMEDOUT, strerror)


# =============================================================================
class GenericLvmHandler(PbBaseHandler):
    """
    Base class for all LVM objects
    """

    # -------------------------------------------------------------------------
    def __init__(
        self, lvm_command=None, lvm_lockfile=DEFAULT_LVM_LOCKFILE,
            lvm_timeout=DEFAULT_LVM_TIMEOUT,
            appname=None, verbose=0, version=__version__, base_dir=None,
            use_stderr=False, initialized=False, simulate=False, sudo=False,
            quiet=False, *targs, **kwargs
            ):
        """
        Initialisation of the generic LVM handler object.

        @raise CommandNotFoundError: if the command 'lvm'
                                     could not be found
        @raise ValueError: On a wrong lvm_timeout
        @raise GenericLvmError: on a uncoverable error.

        @param lvm_command: path to executable 'lvm' command
        @type lvm_command: str
        @param lvm_lockfile: the global lockfile used for lvm execution
        @type lvm_lockfile: str
        @param lvm_timeout: timeout for execution the lvm command
        @type lvm_timeout: int or None

        @param appname: name of the current running application
        @type appname: str
        @param verbose: verbose level
        @type verbose: int
        @param version: the version string of the current object or application
        @type version: str
        @param base_dir: the base directory of all operations
        @type base_dir: str
        @param use_stderr: a flag indicating, that on handle_error() the output
                           should go to STDERR, even if logging has
                           initialized logging handlers.
        @type use_stderr: bool
        @param simulate: don't execute actions, only display them
        @type simulate: bool
        @param sudo: should the command executed by sudo by default
        @type sudo: bool
        @param quiet: don't display ouput of action after calling
        @type quiet: bool

        @return: None

        """

        # /sbin/lvm
        self._lvm_command = LVM_BIN_PATH
        """
        @ivar: the 'lvm' command in operating system
        @type: str
        """

        self._lvm_lockfile = lvm_lockfile
        """
        @ivar: the global lockfile used for lvm execution
        @type: str
        """
        lock_dir = os.path.dirname(self.lvm_lockfile)
        lock_basename = os.path.basename(self.lvm_lockfile)
        if os.path.isdir(lock_dir):
            lock_dir = os.path.realpath(lock_dir)
            self._lvm_lockfile = os.path.join(lock_dir, lock_basename)

        self._lvm_timeout = DEFAULT_LVM_TIMEOUT

        self.locker = None
        """
        @ivar: a handler object for handling locks
        @type: PbLockHandler
        """

        self.global_lock = None
        """
        @ivar: a lock object after successful claiming the global lock.
        @type: PbLock or None
        """

        # Initialisation of the parent object
        super(GenericLvmHandler, self).__init__(
            appname=appname,
            verbose=verbose,
            version=version,
            base_dir=base_dir,
            use_stderr=use_stderr,
            initialized=False,
            simulate=simulate,
            sudo=sudo,
            quiet=quiet,
        )

        failed_commands = []

        # Check of the lvm command
        if lvm_command:
            self._lvm_command = lvm_command
        if not os.path.exists(self._lvm_command):
            failed_commands.append('lvm')

        # Some commands are missing
        if failed_commands:
            raise CommandNotFoundError(failed_commands)

        if lvm_timeout:
            self.lvm_timeout = lvm_timeout

        self.locker = PbLockHandler(
            lockretry_delay_start=0.1,
            lockretry_delay_increase=0.1,
            lockretry_max_delay=15,
            max_lockfile_age=600,
            locking_use_pid=True,
            appname=appname,
            verbose=verbose,
            base_dir=base_dir,
            initialized=False,
            simulate=simulate,
            sudo=sudo,
            quiet=quiet,
        )
        self.locker.initialized = True

        if initialized:
            self.initialized = True
            if self.verbose > 3:
                LOG.debug(_("Initialized."))

    # -------------------------------------------------------------------------
    @property
    def lvm_command(self):
        """The 'lvm' command in operating system."""
        return self._lvm_command

    # -------------------------------------------------------------------------
    @property
    def lvm_lockfile(self):
        """The global lockfile used for lvm execution."""
        return self._lvm_lockfile

    # -------------------------------------------------------------------------
    @property
    def lvm_timeout(self):
        """The timeout for execution the lvm command."""
        return self._lvm_timeout

    @lvm_timeout.setter
    def lvm_timeout(self, value):
        v = int(value)
        if v <= 0:
            msg = _("A timeout must be greater than zero (not %d).") % (v)
            raise ValueError(msg)
        self._lvm_timeout = v

    # -------------------------------------------------------------------------
    def as_dict(self, short=False):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = super(GenericLvmHandler, self).as_dict(short=short)
        res['lvm_command'] = self.lvm_command
        res['lvm_lockfile'] = self.lvm_lockfile
        res['lvm_timeout'] = self.lvm_timeout

        return res

    # -------------------------------------------------------------------------
    def __del__(self):
        """
        Destructor
        """

        self.global_lock = None

    # -------------------------------------------------------------------------
    def lock_global(self):
        """
        Creates a global lock for all executions of 'lvm'.

        @raise CouldntOccupyLockfileError: the lock could not be occupied.

        """

        if self.global_lock:
            msg = _("Global lockfile %r already occupied.")
            LOG.warn(msg, self.lvm_lockfile)
            return

        self.global_lock = self.locker.create_lockfile(self.lvm_lockfile)
        self.global_lock.autoremove = True

    # -------------------------------------------------------------------------
    def unlock_global(self):
        """
        Removes the global mdadm lock.
        """

        self.global_lock = None

    # -------------------------------------------------------------------------
    def exec_lvm(
        self, cmd_params=None, locked=False, release_lock=True,
            quiet=True, simulate=None, sudo=None, force=False):
        """
        Execute 'lvm' serialized by setting a global lock file (or not).

        @raise LvmTimeoutError: On timeout execution of 'lvm'
        @raise LvmExecError: On some errors on execution

        @param cmd_params: all parameters for calling 'lvm' (except --verbose)
        @type cmd_params: list of str
        @param locked: should the execution of 'lvm' be executed after
                       Occupying the global lock
        @type locked: bool
        @param release_lock: should the global lock removed after execution
        @type release_lock: bool
        @param quiet: quiet execution of the command
        @type quiet: bool
        @param simulate: coerced simulation of the command
        @type simulate: bool
        @param sudo: execute 'lvm' with sudo as root
        @type sudo: bool or None
        @param force: dont raise a LvmExecError, if the return value is not zero
        @type force: bool

        @return: a tuple of::
            - return value of lvm,
            - output on STDOUT,
            - output on STDERR

        """

        if not cmd_params:
            msg = _("No arguments given on calling %s()." % ('exec_lvm'))
            raise LvmExecError(msg)

        cmd = [self.lvm_command]
        if self.verbose > 1 and not quiet:
            cmd.append('--verbose')

        if isinstance(cmd_params, list):
            for p in cmd_params:
                cmd.append(p)
        else:
            cmd.append(str(cmd_params))
        cmd = [str(element) for element in cmd]

        do_sudo = False
        if os.geteuid():
            do_sudo = True
        if sudo is not None:
            do_sudo = bool(sudo)
        if do_sudo:
            LOG.debug(_("Executing as root:") + " %s", cmd_str)
        else:
            LOG.debug(_("Executing:") + " %s", cmd_str)

        if locked and not self.global_lock:
            self.lock_global()

        ret_code = None
        std_out = None
        std_err = None

        def exec_alarm_caller(signum, sigframe):
            '''
            This nested function will be called in event of a timeout

            @param signum:   the signal number (POSIX) which happend
            @type signum:    int
            @param sigframe: the frame of the signal
            @type sigframe:  object
            '''

            cmd_str = ' '.join(map(lambda x: pipes.quote(x), cmd))
            raise LvmTimeoutError(self.lvm_timeout, cmd_str)

        if self.verbose > 1:
            LOG.debug(__(
                "Timeout on executing: %d second.",
                "Timeout on executing: %d seconds.",
                self.lvm_timeout), self.lvm_timeout)
        signal.signal(signal.SIGALRM, exec_alarm_caller)
        signal.alarm(self.lvm_timeout)
        try:
            (ret_code, std_out, std_err) = self.call(
                cmd, quiet=quiet, sudo=do_sudo, simulate=simulate)

            if ret_code and not force:
                cmd_str = ' '.join(map(lambda x: pipes.quote(x), cmd))
                msg = _("Error %(rc)d executing \"%(cmd)s\": %(msg)s") % {
                    'rc': ret_code, 'cmd': cmd_str, 'msg': std_err}
                raise LvmExecError(msg)

        finally:
            signal.alarm(0)
            if locked and release_lock:
                self.global_lock = None

        return (ret_code, std_out, std_err)


# =============================================================================

if __name__ == "__main__":

    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
