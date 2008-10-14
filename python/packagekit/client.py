#!/usr/bin/python
#
# Licensed under the GNU General Public License Version 2
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# (c) 2008
#    Canonical Ltd.
#    Aidan Skinner <aidan@skinner.me.uk>
#    Martin Pitt <martin.pitt@ubuntu.com>
#    Tim Lauridsen <timlau@fedoraproject.org>
#
# Synchronous PackageKit client wrapper API for Python.

import os
import gobject
import dbus
from enums import *
from misc import *

__api_version__ = '0.1.0'

class PackageKitError(Exception):
    '''PackageKit error.

    This class mainly wraps a PackageKit "error enum". See
    http://www.packagekit.org/pk-reference.html#introduction-errors for details
    and possible values.
    '''
    def __init__(self, error, desc=None):
        self.error = error
        self.desc = desc

    def __str__(self):
        return "%s: %s" % (self.error, self.desc)

class PackageKitClient:
    '''PackageKit client wrapper class.

    This exclusively uses synchonous calls. Functions which take a long time
    (install/remove packages) have callbacks for progress feedback.
    '''
    def __init__(self, main_loop=None):
        '''Initialize a PackageKit client.

        If main_loop is None, this sets up its own gobject.MainLoop(),
        otherwise it attaches to the specified one.
        '''
        self.pk_control = None
        if main_loop is None:
            import dbus.mainloop.glib
            main_loop = gobject.MainLoop()
            dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.main_loop = main_loop

        self.bus = dbus.SystemBus()

    def _wrapCall(self, pk_xn, method, callbacks):
        '''
        Wraps a call which emits Finished and ErrorCode on completion
        '''
        pk_xn.connect_to_signal('Finished', self._h_finished)
        pk_xn.connect_to_signal('ErrorCode', self._h_error)
        for cb in callbacks.keys():
            pk_xn.connect_to_signal(cb, callbacks[cb])

        polkit_auth_wrapper(method)
        self._wait()
        if self._error_enum:
            raise PackageKitError(self._error_enum, self._error_desc)

    def _wrapBasicCall(self, pk_xn, method):
        return self._wrapCall(pk_xn, method, {})

    def _wrapPackageCall(self, pk_xn, method):
        '''
        Wraps a call which emits Finished, ErrorCode on completion and
        Package for information returns a list of dicts with
        'installed', 'id' and 'summary' keys
        '''

        result = []
        package_cb = lambda i, id, summary: result.append(
            PackageKitPackage(i, id, summary))
        self._wrapCall(pk_xn, method, {'Package' : package_cb})
        return result

    def _wrapDistroUpgradeCall(self, pk_xn, method):
        '''
        Wraps a call which emits Finished, ErrorCode on completion and
        DistroUpgrade for information returns a list of dicts with
        'type', 'name' and 'summary' keys
        '''

        result = []
        distup_cb = lambda typ, name, summary: result.append(
            PackageKitDistroUpgrade(typ, name, summary))
        self._wrapCall(pk_xn, method, {'DistroUpgrade' : distup_cb})
        return result

    def _wrapDetailsCall(self, pk_xn, method):
        '''
        Wraps a call which emits Finished, ErrorCode on completion and
        Details for information returns a list of dicts with 'id',
        'license', 'group', 'description', 'upstream_url', 'size'.keys
        '''
        result = []
        details_cb = lambda id, license, group, detail, url, size: result.append(
            PackageKitDetails(id, license, group, detail, url, size))

        self._wrapCall(pk_xn, method, {'Details' : details_cb})
        return result

    def _wrapCategoryCall(self, pk_xn, method):
        '''
        Wraps a call which emits Finished, ErrorCode on completion and
        Details for information returns a list of dicts with 'id',
        'license', 'group', 'description', 'upstream_url', 'size'.keys
        '''
        result = []
        category_cb = lambda  parent_id, cat_id, name, summary, icon: result.append(
            PackageKitCategory( parent_id, cat_id, name, summary, icon))

        self._wrapCall(pk_xn, method, {'Category' : category_cb})
        return result

    def _wrapUpdateDetailsCall(self, pk_xn, method):
        '''
        Wraps a call which emits Finished, ErrorCode on completion and
        Details for information returns a list of dicts with 'id',
        'license', 'group', 'description', 'upstream_url', 'size'.keys
        '''
        result = []
        details_cb =  lambda id, updates, obsoletes, vendor_url, bugzilla_url, \
                             cve_url, restart, update_text, changelog, state, \
                             issued, updated: result.append(
            PackageKitUpdateDetails(id, updates, obsoletes, vendor_url, bugzilla_url, \
                                    cve_url, restart, update_text, changelog, state, \
                                    issued, updated))
        self._wrapCall(pk_xn, method, {'UpdateDetail' : details_cb})
        return result

    def _wrapReposCall(self, pk_xn, method):
        '''
        Wraps a call which emits Finished, ErrorCode and RepoDetail
        for information returns a list of dicts with 'id',
        'description', 'enabled' keys
        '''
        result = []
        repo_cb = lambda id, description, enabled: result.append(
            PackageKitRepos(id, description, enabled))
        self._wrapCall(pk_xn, method, {'RepoDetail' : repo_cb})
        return result

    def _wrapFilesCall(self, pk_xn, method):
        '''
        Wraps a call which emits Finished, ErrorCode and Files
        for information returns a list of dicts with 'id',
        'files'
        '''
        result = []
        files_cb = lambda id, files: result.append(
            PackageKitFiles(id, files))
        self._wrapCall(pk_xn, method, {'Files' : files_cb})
        return result

    def SuggestDaemonQuit(self):
        '''Ask the PackageKit daemon to shutdown.'''

        try:
            self.pk_control.SuggestDaemonQuit()
        except (AttributeError, dbus.DBusException), e:
            # not initialized, or daemon timed out
            pass

    def Resolve(self, filters, package):
        '''
        Resolve a package name to a PackageKit package_id filters and
        package are directly passed to the PackageKit transaction
        D-BUS method Resolve()

        Return Dict with keys of (installed, id, short_description)
        for all matches, where installed is a boolean and id and
        short_description are strings.
        '''
        package = self._to_list(package) # Make sure we have a list
        xn = self._get_xn()
        return self._wrapPackageCall(xn, lambda : xn.Resolve(filters, package))

    def GetDetails(self, package_ids):
        '''
        Get details about a PackageKit package_ids.

        Return dict with keys (id, license, group, description,
        upstream_url, size).
        '''
        package_ids = self._to_list(package_ids) # Make sure we have a list
        xn = self._get_xn()
        return self._wrapDetailsCall(xn, lambda : xn.GetDetails(package_ids))

    def SearchName(self, filters, name):
        '''
        Search a package by name.
        '''
        xn = self._get_xn()
        return self._wrapPackageCall(xn, lambda : xn.SearchName(filters, name))

    def SearchGroup(self, filters, group_id):
        '''
        Search for a group.
        '''
        xn = self._get_xn()
        return self._wrapPackageCall(xn, lambda : xn.SearchGroup(filters, group_id))

    def SearchDetails(self, filters, name):
        '''
        Search a packages details.
        '''
        xn = self._get_xn()
        return self._wrapPackageCall(xn,
                                     lambda : xn.SearchDetails(filters, name))

    def SearchFile(self, filters, search):
        '''
        Search for a file.
        '''
        xn = self._get_xn()
        return self._wrapPackageCall(xn,
                                     lambda : xn.SearchFile(filters, search))

    def InstallPackages(self, package_ids, progress_cb=None):
        '''Install a list of package IDs.

        progress_cb is a function taking arguments (status, percentage,
        subpercentage, elapsed, remaining, allow_cancel). If it returns False,
        the action is cancelled (if allow_cancel == True), otherwise it
        continues.

        On failure this throws a PackageKitError or a DBusException.
        '''
        package_ids = self._to_list(package_ids) # Make sure we have a list
        xn = self._get_xn()
        self._doPackages( xn, lambda : xn.InstallPackages(package_ids), progress_cb)

    def UpdatePackages(self, package_ids, progress_cb=None):
        '''UPdate a list of package IDs.

        progress_cb is a function taking arguments (status, percentage,
        subpercentage, elapsed, remaining, allow_cancel). If it returns False,
        the action is cancelled (if allow_cancel == True), otherwise it
        continues.

        On failure this throws a PackageKitError or a DBusException.
        '''
        package_ids = self._to_list(package_ids) # Make sure we have a list
        xn = self._get_xn()
        self._doPackages(xn, lambda : xn.UpdatePackages(package_ids), progress_cb)

    def RemovePackages(self, package_ids, progress_cb=None, allow_deps=False,
        auto_remove=True):
        '''Remove a list of package IDs.

        progress_cb is a function taking arguments (status, percentage,
        subpercentage, elapsed, remaining, allow_cancel). If it returns False,
        the action is cancelled (if allow_cancel == True), otherwise it
        continues.

        allow_deps and auto_remove are passed to the PackageKit function.

        On failure this throws a PackageKitError or a DBusException.
        '''
        package_ids = self._to_list(package_ids) # Make sure we have a list
        xn = self._get_xn()
        self._doPackages(xn, lambda : xn.RemovePackages(package_ids, allow_deps, auto_remove), progress_cb)

    def RefreshCache(self, force=False):
        '''
        Refresh the cache, i.e. download new metadata from a
        remote URL so that package lists are up to date. This action
        may take a few minutes and should be done when the session and
        system are idle.
        '''
        xn = self._get_xn()
        self._wrapBasicCall(xn, lambda : xn.RefreshCache(force))

    def GetRepoList(self, filters=FILTER_NONE):
        '''
        Returns the list of repositories used in the system

        filter is a correct filter, e.g. None or 'installed;~devel'

        '''
        xn = self._get_xn()
        return self._wrapReposCall(xn, lambda : xn.GetRepoList(filters))

    def RepoEnable(self, repo_id, enabled):
        '''
        Enables the repository specified.

        repo_id is a repository identifier, e.g. fedora-development-debuginfo

        enabled true if enabled, false if disabled

        '''
        xn = self._get_xn()
        self._wrapBasicCall(xn, lambda : xn.RepoEnable(repo_id, enabled))

    def GetUpdates(self, filters=FILTER_NONE):
        '''
        This method should return a list of packages that are installed and
        are upgradable.

        It should only return the newest update for each installed package.
        '''
        xn = self._get_xn()
        return self._wrapPackageCall(xn, lambda : xn.GetUpdates(filters))

    def GetCategories(self):
        '''
        This method should return a list of Categories
        '''
        xn = self._get_xn()
        return self._wrapCategoryCall(xn, lambda : xn.GetCategories())

    def GetPackages(self, filters=FILTER_NONE):
        '''
        This method should return a total list of packages, limited by the
        filters used
        '''
        xn = self._get_xn()
        return self._wrapPackageCall(xn, lambda : xn.GetPackages(filters))

    def UpdateSystem(self, progress_cb=None):
        '''
        This method should update the system
        '''
        xn = self._get_xn()
        self._doPackages(xn, lambda : xn.UpdateSystem(), progress_cb)

    def DownloadPackages(self, package_ids):
        package_ids = self._to_list(package_ids) # Make sure we have a list
        xn = self._get_xn()
        return self._wrapFilesCall(xn, lambda : xn.DownloadPackages(package_ids))

    def GetDepends(self, filters, package_ids, recursive=False):
        '''
        Search for dependencies for packages
        '''
        package_ids = self._to_list(package_ids) # Make sure we have a list
        xn = self._get_xn()
        return self._wrapPackageCall(xn,
                                     lambda : xn.GetDepends(filters, package_ids, recursive))

    def GetFiles(self, package_ids):
        package_ids = self._to_list(package_ids) # Make sure we have a list
        xn = self._get_xn()
        return self._wrapFilesCall(xn, lambda : xn.GetFiles(package_ids))

    def GetRequires(self, filters, package_ids, recursive=False):
        '''
        Search for requirements for packages
        '''
        package_ids = self._to_list(package_ids) # Make sure we have a list
        xn = self._get_xn()
        return self._wrapPackageCall(xn,
                                     lambda : xn.GetRequires(filters, package_ids, recursive))

    def GetUpdateDetail(self, package_ids):
        '''
        Get details for updates
        '''
        package_ids = self._to_list(package_ids) # Make sure we have a list
        xn = self._get_xn()
        return self._wrapUpdateDetailsCall(xn, lambda : xn.GetUpdateDetail(package_ids))

    def GetDistroUpgrades(self):
        xn = self._get_xn()
        return self._wrapPackageCall(xn, lambda : xn.GetDistroUpgrades())

    def InstallFiles(self, trusted, files):
        raise PackageKitError(ERROR_NOT_SUPPORTED)

    def InstallSignatures(self, sig_type, key_id, package_id):
        '''
        Install packages signing keys used to validate packages
        '''
        xn = self._get_xn()
        self._wrapBasicCall(xn, lambda : xn.InstallSignatures(sig_type, key_id, package_id))

    def RepoSetData(self, repo_id, parameter, value):
        '''
        Change custom parameter in Repository Configuration
        '''
        xn = self._get_xn()
        self._wrapBasicCall(xn, lambda : xn.RepoSetData(repo_id, parameter, value))

    def Rollback(self, transaction_id):
        xn = self._get_xn()
        self._wrapBasicCall(xn, lambda : xn.Rollback(transaction_id))

    def WhatProvides(self, provide_type, search):
        '''
        Search for packages that provide the supplied attributes
        '''
        xn = self._get_xn()
        return self._wrapPackageCall(xn,
                                     lambda : xn.WhatProvides(provide_type, search))

    def SetLocale(self, code):
        xn = self._get_xn()
        xn.SetLocale(code)

    def AcceptEula(self, eula_id):
        xn = self._get_xn()
        self._wrapBasicCall(xn, lambda : xn.AcceptEula(eula_id))

    #
    # Internal helper functions
    #
    def _to_list(self, obj):
        '''convert obj to list'''
        if isinstance(obj, str):
            obj = [obj]
        return obj

    def _wait(self):
        '''Wait until an async PK operation finishes.'''
        self.main_loop.run()

    def _h_status(self, status):
        '''
        StatusChanged signal handler
        '''
        self._status = status

    def _h_allowcancel(self, allow):
        '''
        AllowCancel signal handler
        '''
        self._allow_cancel = allow

    def _h_error(self, enum, desc):
        '''
        ErrorCode signal handler
        '''
        self._error_enum = enum
        self._error_desc = desc

    def _h_finished(self, status, code):
        '''
        Finished signal handler
        '''
        self._finished_status = status
        self.main_loop.quit()

    def _h_progress(self, per, subper, el, rem):
        '''
        ProgressChanged signal handler
        '''
        def _cancel(xn):
            try:
                xn.Cancel()
            except dbus.DBusException, e:
                if e._dbus_error_name == 'org.freedesktop.PackageKit.Transaction.CannotCancel':
                    pass
                else:
                    raise

        ret = self._progress_cb(self._status, int(per),
            int(subper), int(el), int(rem), self._allow_cancel)
        if not ret:
            # we get backend timeout exceptions more likely when we call this
            # directly, so delay it a bit
            gobject.timeout_add(10, _cancel, pk_xn)

    def _auth(self):
        policykit = self.bus.get_object(
            'org.freedesktop.PolicyKit.AuthenticationAgent', '/',
            'org.freedesktop.PolicyKit.AuthenticationAgent')
        if(policykit == None):
            print("Error: Could not get PolicyKit D-Bus Interface\n")
        granted = policykit.ObtainAuthorization("org.freedesktop.packagekit.update-system",
                                                (dbus.UInt32)(xid),
                                                (dbus.UInt32)(os.getpid()))

    def _doPackages(self, pk_xn, method, progress_cb):
        '''Shared implementation of InstallPackages, UpdatePackages and RemovePackages.'''

        self._status = None
        self._allow_cancel = False

        if progress_cb:
            pk_xn.connect_to_signal('StatusChanged', self._h_status)
            pk_xn.connect_to_signal('AllowCancel', self._h_allowcancel)
            pk_xn.connect_to_signal('ProgressChanged', self._h_progress)
            self._progress_cb = progress_cb
        self._wrapBasicCall(pk_xn, method)
        if self._finished_status != 'success':
            raise PackageKitError('internal-error')

    def _get_xn(self):
        '''Create a new PackageKit Transaction object.'''

        self._error_enum = None
        self._error_desc = None
        self._finished_status = None
        try:
            tid = self.pk_control.GetTid()
        except (AttributeError, dbus.DBusException), e:
            if self.pk_control == None or (hasattr(e, '_dbus_error_name') and \
                e._dbus_error_name == 'org.freedesktop.DBus.Error.ServiceUnknown'):
                # first initialization (lazy) or timeout
                self.pk_control = dbus.Interface(self.bus.get_object(
                        'org.freedesktop.PackageKit',
                        '/org/freedesktop/PackageKit',
                    False), 'org.freedesktop.PackageKit')
                tid = self.pk_control.GetTid()
            else:
                raise

        return dbus.Interface(self.bus.get_object('org.freedesktop.PackageKit',
            tid, False), 'org.freedesktop.PackageKit.Transaction')

#### PolicyKit authentication borrowed wrapper ##
class PermissionDeniedByPolicy(dbus.DBusException):
    _dbus_error_name = 'org.freedesktop.PackageKit.Transaction.RefusedByPolicy'

def polkit_auth_wrapper(fn, *args, **kwargs):
    '''Function call wrapper for PolicyKit authentication.

    Call fn(*args, **kwargs). If it fails with a PermissionDeniedByPolicy
    and the caller can authenticate to get the missing privilege, the PolicyKit
    authentication agent is called, and the function call is attempted again.
    '''
    try:
        return fn(*args, **kwargs)
    except dbus.DBusException, e:
        if e._dbus_error_name == PermissionDeniedByPolicy._dbus_error_name:
            # last words in message are privilege and auth result
            (priv, auth_result) = e.message.split()[-2:]
            if auth_result.startswith('auth_'):
                pk_auth = dbus.SessionBus().get_object(
                    'org.freedesktop.PolicyKit.AuthenticationAgent', '/', 'org.gnome.PolicyKit.AuthorizationManager.SingleInstance')

                # TODO: provide xid
                res = pk_auth.ObtainAuthorization(priv, dbus.UInt32(0),
                    dbus.UInt32(os.getpid()), timeout=300)
                print res
                if res:
                    return fn(*args, **kwargs)
            raise PermissionDeniedByPolicy(priv + ' ' + auth_result)
        else:
            raise

if __name__ == '__main__':
    pass
