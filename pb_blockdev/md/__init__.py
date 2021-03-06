#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank.brehm@profitbricks.com
@copyright: © 2010 - 2015 by Frank Brehm, Berlin
@summary: All modules for handling md devices and commands
"""

# Standard modules
import os
import re
import logging
import socket
import uuid
import signal
import errno

# Third party modules

# Own modules
from pb_base.handler import CommandNotFoundError
from pb_base.handler import PbBaseHandler

from pb_base.handler.lock import PbLockHandler

from pb_blockdev.base import BlockDeviceError

from pb_blockdev.translate import pb_gettext, pb_ngettext

_ = pb_gettext
__ = pb_ngettext

__version__ = '0.2.5'

MDADM_PATH = os.sep + os.path.join('sbin', 'mdadm')
LOG = logging.getLogger(__name__)

DEFAULT_MDADM_LOCKFILE = os.sep + os.path.join('tmp', 'mdadm-vcb.lock')
MY_HOSTNAME = socket.gethostname()
if MY_HOSTNAME.startswith('storage'):
    DEFAULT_MDADM_LOCKFILE = os.sep + os.path.join('tmp', 'storage-mdadm.lock')
del MY_HOSTNAME

DEFAULT_MDADM_TIMEOUT = 15

MDADM_MODES = {
    'assemble': '--assemble',
    'build': '--build',
    'create': '--create',
    'monitor': '--monitor',
    'grow': '--grow',
    'incremental': '--incremental',
    'auto-detect': '--auto-detect',
    'manage': None,
}
"""
Possible mdadm mode descriptions and their appropriate command line parameter.
"""

MD_UUID_TOKEN = r'[0-9a-f]{8}'
MD_UUID_PATTERN = MD_UUID_TOKEN + r':' + MD_UUID_TOKEN + r':' + \
    MD_UUID_TOKEN + r':' + MD_UUID_TOKEN + r'$'
RE_MD_UUID = re.compile(MD_UUID_PATTERN, re.IGNORECASE)


# =============================================================================
def is_md_uuid(src_uuid):
    """
    Gives back, whether the given string is a UUID in the
    special format of mdadm.

    @return: src_uuid is a MD formatted UUID
    @rtype: bool

    """

    if isinstance(src_uuid, str):
        if RE_MD_UUID.search(src_uuid):
            return True
    return False


# =============================================================================
def uuid_to_md(src_uuid):
    """
    Transforms a UUID into the format, mdadm is using it::
        8f81b25c-be12-486e-a4da-eb49f02379f3 -> 8f81b25c:be12486e:a4daeb49:f02379f3

    @param src_uuid: the UUID to transform
    @type src_uuid: uuid

    @raise ValueError: if src_uuid is an invalid UUID

    @return: the UUID in the MD format
    @rtype: str

    """

    uuid_raw = uuid.UUID(str(src_uuid))
    uuid_str = str(uuid_raw).replace('-', '')
    uuid_md = (
        uuid_str[0:8] + ':' + uuid_str[8:16] + ':' + uuid_str[16:24] +
        ':' + uuid_str[24:32])

    return uuid_md


# =============================================================================
def uuid_from_md(src_uuid):
    """
    The opposite of uuid_to_md()::
        8f81b25c:be12486e:a4daeb49:f02379f3 -> 8f81b25c-be12-486e-a4da-eb49f02379f3

    @param src_uuid: the UUID to transform
    @type src_uuid: uuid

    @raise ValueError: if src_uuid is an invalid UUID

    @return: an UUID object
    @rtype: uuid

    """

    uuid_str = src_uuid.strip().replace(':', '')
    return uuid.UUID(uuid_str)


# =============================================================================
class GenericMdError(BlockDeviceError):
    """Base exception class for all md-raid errors"""
    pass


# =============================================================================
class MdadmError(GenericMdError):
    """Exception class for errors on executing mdadm"""
    pass


# =============================================================================
class MdadmTimeoutError(MdadmError, IOError):
    """Special exception class for timeout on execution of mdadm."""

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

        super(MdadmTimeoutError, self).__init__(errno.ETIMEDOUT, strerror)


# =============================================================================
class GenericMdHandler(PbBaseHandler):
    """
    Base class for all MD raid objects
    """

    # -------------------------------------------------------------------------
    def __init__(
        self, mdadm_command=None, mdadm_lockfile=DEFAULT_MDADM_LOCKFILE,
            mdadm_timeout=DEFAULT_MDADM_TIMEOUT,
            appname=None, verbose=0, version=__version__, base_dir=None,
            use_stderr=False, initialized=False, simulate=False, sudo=False,
            quiet=False, *targs, **kwargs
            ):
        """
        Initialisation of the generic mdraid handler object.

        @raise CommandNotFoundError: if the command 'mdadm'
                                     could not be found
        @raise ValueError: On a wrong mdadm_timeout
        @raise GenericMdError: on a uncoverable error.

        @param mdadm_command: path to executable mdadm command
        @type mdadm_command: str
        @param mdadm_lockfile: the global lockfile used for mdadm execution
        @type mdadm_lockfile: str
        @param mdadm_timeout: timeout for execution the mdadm command
        @type mdadm_timeout: int or None

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

        # /sbin/mdadm
        self._mdadm_command = MDADM_PATH
        """
        @ivar: the 'mdadm' command in operating system
        @type: str
        """

        self._mdadm_lockfile = mdadm_lockfile
        """
        @ivar: the global lockfile used for mdadm execution
        @type: str
        """

        self._mdadm_timeout = DEFAULT_MDADM_TIMEOUT

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
        super(GenericMdHandler, self).__init__(
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

        # Check of the mdadm command
        if mdadm_command:
            self._mdadm_command = mdadm_command
        if not os.path.exists(self._mdadm_command):
            failed_commands.append('mdadm')

        # Some commands are missing
        if failed_commands:
            raise CommandNotFoundError(failed_commands)

        if mdadm_timeout:
            self.mdadm_timeout = mdadm_timeout

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
    def mdadm_command(self):
        """The 'mdadm' command in operating system."""
        return self._mdadm_command

    # -------------------------------------------------------------------------
    @property
    def mdadm_lockfile(self):
        """The global lockfile used for mdadm execution."""
        return self._mdadm_lockfile

    # -------------------------------------------------------------------------
    @property
    def mdadm_timeout(self):
        """The timeout for execution the mdadm command."""
        return self._mdadm_timeout

    @mdadm_timeout.setter
    def mdadm_timeout(self, value):
        v = int(value)
        if v <= 0:
            msg = _("A timeout must be greater than zero (not %d).") % (v)
            raise ValueError(msg)
        self._mdadm_timeout = v

    # -------------------------------------------------------------------------
    def as_dict(self, short=False):
        """
        Transforms the elements of the object into a dict

        @param short: don't include local properties in resulting dict.
        @type short: bool

        @return: structure as dict
        @rtype:  dict
        """

        res = super(GenericMdHandler, self).as_dict(short=short)
        res['mdadm_command'] = self.mdadm_command
        res['mdadm_lockfile'] = self.mdadm_lockfile
        res['mdadm_timeout'] = self.mdadm_timeout

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
        Creates a global lock for all executions of 'mdadm'.

        @raise CouldntOccupyLockfileError: the lock could not be occupied.

        """

        if self.global_lock:
            msg = _("Global lockfile %r already occupied.")
            LOG.warn(msg, self.mdadm_lockfile)
            return

        self.global_lock = self.locker.create_lockfile(self.mdadm_lockfile)
        self.global_lock.autoremove = True

    # -------------------------------------------------------------------------
    def unlock_global(self):
        """
        Removes the global mdadm lock.
        """

        self.global_lock = None

    # -------------------------------------------------------------------------
    def exec_mdadm(
        self, mode='manage', cmd_params=None, locked=False, release_lock=True,
            quiet=True, simulate=None, sudo=None, force=False):
        """
        Execute 'mdadm' serialized by setting a global lock file (or not).

        @raise MdadmTimeoutError: On timeout execution of mdadm
        @raise MdadmError: On some errors on execution

        @param mode: the execution mode of 'mdadm', must be one of the keys
                     of MDADM_MODES
        @type mode: str
        @param cmd_params: all parameters for calling mdadm (except --verbose)
        @type cmd_params: list of str
        @param locked: should the execution of mdadm be executed after
                       Occupying the global lock
        @type locked: bool
        @param release_lock: should the global lock removed after execution
        @type release_lock: bool
        @param quiet: quiet execution of the command
        @type quiet: bool
        @param simulate: coerced simulation of the command
        @type simulate: bool
        @param sudo: execute mdadm with sudo as root
        @type sudo: bool or None
        @param force: dont raise a MdadmError, if the return value is not zero
        @type force: bool

        @return: a tuple of::
            - return value of mdadm,
            - output on STDOUT,
            - output on STDERR

        """

        if not cmd_params:
            msg = _("No arguments given on calling exec_mdadm().")
            raise MdadmError(msg)

        if mode not in MDADM_MODES:
            msg = _("Invalid mode %r on calling exec_mdadm() given.") % (mode)
            raise MdadmError(msg)
        mode_arg = MDADM_MODES[mode]

        cmd = [self.mdadm_command]
        cmd_str = self.mdadm_command

        if mode_arg:
            cmd.append(mode_arg)
            cmd_str += " " + mode_arg
        if self.verbose > 1 and not quiet:
            cmd.append('--verbose')
            cmd_str += " --verbose"

        if isinstance(cmd_params, list):
            for p in cmd_params:
                cmd.append(p)
                cmd_str += " " + ("%r" % (str(p)))
        else:
            cmd.append(str(cmd_params))
            cmd_str += " " + ("%r" % (str(cmd_params)))

        do_sudo = False
        if os.geteuid():
            do_sudo = True
        if sudo is not None:
            do_sudo = bool(sudo)
        if do_sudo:
            LOG.debug(
                _("Executing as root:") + " %s",
                cmd_str)
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

            raise MdadmTimeoutError(self.mdadm_timeout, cmd_str)

        if self.verbose > 1:
            LOG.debug(__(
                "Timeout on executing: %d second.",
                "Timeout on executing: %d seconds.",
                self.mdadm_timeout), self.mdadm_timeout)
        signal.signal(signal.SIGALRM, exec_alarm_caller)
        signal.alarm(self.mdadm_timeout)
        try:
            (ret_code, std_out, std_err) = self.call(
                cmd, quiet=quiet, sudo=do_sudo, simulate=simulate)

            if ret_code and not force:
                msg = _("Error %(rc)d executing \"%(cmd)s\": %(msg)s") % {
                    'rc': ret_code, 'cmd': cmd_str, 'msg': std_err}
                raise MdadmError(msg)

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
