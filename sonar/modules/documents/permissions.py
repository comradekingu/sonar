# -*- coding: utf-8 -*-
#
# Swiss Open Access Repository
# Copyright (C) 2019 RERO
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Permissions for documents."""

from flask import request

from sonar.modules.documents.api import DocumentRecord
from sonar.modules.organisations.api import OrganisationRecord, \
    current_organisation
from sonar.modules.permissions import RecordPermission
from sonar.modules.users.api import current_user_record


class DocumentPermission(RecordPermission):
    """Documents permissions."""

    @classmethod
    def list(cls, user, record=None):
        """List permission check.

        :param user: Logged user.
        :param recor: Record to check.
        :returns: True is action can be done.
        """
        view = request.args.get('view')

        # Documents are accessess in public view, but eventually filtered later
        # by organisation
        if view:
            return True

        # Only for moderators users.
        if (not current_user_record or not current_user_record.is_moderator or
                not current_organisation):
            return False

        return True

    @classmethod
    def create(cls, user, record=None):
        """Create permission check.

        :param user: Logged user.
        :param recor: Record to check.
        :returns: True is action can be done.
        """
        # Only for moderators users
        return current_user_record and current_user_record.is_moderator

    @classmethod
    def read(cls, user, record):
        """Read permission check.

        :param user: Logged user.
        :param recor: Record to check.
        :returns: True is action can be done.
        """
        # Only for moderator users.
        if not current_user_record or not current_user_record.is_moderator:
            return False

        # Superuser is allowed.
        if current_user_record.is_superuser:
            return True

        document = DocumentRecord.get_record_by_pid(record['pid'])
        document = document.replace_refs()

        # For admin or moderators users, they can access only to their
        # organisation's documents.
        return current_organisation['pid'] == document['organisation']['pid']

    @classmethod
    def update(cls, user, record):
        """Update permission check.

        :param user: Logged user.
        :param recor: Record to check.
        :returns: True is action can be done.
        """
        # Same rules as read
        return cls.read(user, record)

    @classmethod
    def delete(cls, user, record):
        """Delete permission check.

        :param user: Logged user.
        :param recor: Record to check.
        :returns: True is action can be done.
        """
        # Delete is only for admins.
        if not current_user_record or not current_user_record.is_admin:
            return False

        # Same rules as read
        return cls.read(user, record)
