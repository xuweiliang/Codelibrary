# Copyright 2013 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Possible actions on an instance.

Actions should probably match a user intention at the API level.  Because they
can be user visible that should help to avoid confusion.  For that reason they
tend to maintain the casing sent to the API.

Maintaining a list of actions here should protect against inconsistencies when
they are used.
"""


CREATE = 'Create Instance'
DELETE = 'Delete Instance'
UPDATE = 'Update Instance'
EVACUATE = 'Evacuate'
RESTORE = 'Restore Instance'
STOP = 'Stop Instance'
START = 'Start Instance'
REBOOT = 'Reboot Instance'
REBUILD = 'Rebuild Instance'
REVERT_RESIZE = 'Revert Resize'
CONFIRM_RESIZE = 'Confirm Resize'
RESIZE = 'Resize Instance'
MIGRATE = 'Migrate'
PAUSE = 'Pause'
UNPAUSE = 'Unpause'
SUSPEND = 'Suspend'
RESUME = 'Resume'
RESCUE = 'Rescue'
UNRESCUE = 'Unrescue'
CHANGE_PASSWORD = 'Change Password'
SHELVE = 'Shelve'
UNSHELVE = 'Unshelve'
CREATESNAPSHOT = 'Create Snapshot'
CREATEDEVSNAPSHOT = 'Create Devsnapshot'
REVERTDEVSNAPSHOT = 'Revert Devsnapshot'
DELETEDEVSNAPSHOT = 'Delete Devsnapshot'
UPDATENAME = 'Update Name'
UPDATEUSB = 'Update USB'
UPDATESCREEN = 'Update Screen'
REALLOCATE = 'Reallocate Instance'
CDROM = 'Attach/Detach CDrom'
CREATEAGGREGATE = 'Create Aggregate'
UPDATEAGGREGATE = 'Update Aggregate'
DELETEAGGREGATE = 'Delete Aggregate'
CREATEFLAVOR = 'Create Flavor'
DELETEFLAVOR = 'Delete Flavor'
SUCCESS = 'Success'
FAILURE = 'Failure'
CREATETEMPLATE = 'Create Template'
ATTACH = 'Attach Volume'
DETACH = 'Detach Volume'
COMMITINSTANCE = 'Commit Instance'
UPDATESECURE= 'Update Spice Security'
CLIPBOARD = 'Update Clipboard Policy'
