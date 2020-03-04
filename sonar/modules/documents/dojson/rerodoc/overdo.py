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

"""Overdo specialized class for RERODOC DOJSON transformation."""

import csv
import os
import re

from flask import current_app

from sonar.modules.documents.dojson.overdo import Overdo as BaseOverdo
from sonar.modules.institutions.api import InstitutionRecord


class Overdo(BaseOverdo):
    """Overdo specialized class for RERODOC DOJSON transformation."""

    affiliations = []
    registererd_organizations = []

    @staticmethod
    def create_institution(institution_key):
        """Create institution if not existing and return it.

        :param str institution_key: Key (PID) of the institution.
        """
        if not institution_key:
            raise Exception('No key provided')

        # Get institution record from database
        organization = InstitutionRecord.get_record_by_pid(institution_key)

        if not organization:
            # Create organization record
            organization = InstitutionRecord.create(
                {
                    'pid': institution_key,
                    'name': institution_key
                },
                dbcommit=True)
            organization.reindex()

    @staticmethod
    def extract_date(date=None):
        """Try to extract date of birth and date of death from field.

        :param date: String, date to parse
        :returns: Tuple containing date of birth and date of death
        """
        if not date:
            return (None, None)

        # Match a full date
        match = re.search(r'^([0-9]{4}-[0-9]{2}-[0-9]{2})$', date)
        if match:
            return (match.group(1), None)

        match = re.search(r'^([0-9]{2}-[0-9]{2}-[0-9]{4})$', date)
        if match:
            return (match.group(1), None)

        # Match these value: "1980-2010"
        match = re.search(r'^([0-9]{4})-([0-9]{4})$', date)
        if match:
            return (match.group(1), match.group(2))

        # Match these value: "1980-" or "1980"
        match = re.search(r'^([0-9]{4})-?', date)
        if match:
            return (match.group(1), None)

        raise Exception('Date "{date}" is not recognized'.format(date=date))

    @staticmethod
    def load_affiliations():
        """Load affiliations from reference file."""
        csv_file = os.path.dirname(
            __file__) + '/../../../../../data/affiliations.csv'

        Overdo.affiliations = []

        with open(csv_file, 'r') as file:
            reader = csv.reader(file, delimiter='\t')
            for row in reader:
                affiliation = []
                for index, value in enumerate(row):
                    if index > 0 and value:
                        affiliation.append(value)

                if affiliation:
                    Overdo.affiliations.append(affiliation)

    def do(self, blob, ignore_missing=True, exception_handlers=None):
        """Do transformation."""
        result = super(Overdo, self).do(blob,
                                        ignore_missing=ignore_missing,
                                        exception_handlers=exception_handlers)

        # Verify data integrity
        self.verify(result)

        return result

    def get_affiliations(self, full_affiliation):
        """Get controlled affiliations list based on reference CSV file.

        :param full_affiliation: String representing complete affiliation
        """
        if not full_affiliation:
            return []

        if not self.affiliations:
            self.load_affiliations()

        full_affiliation = full_affiliation.lower()

        controlled_affiliations = []

        for affiliations in self.affiliations:
            for affiliation in affiliations:
                if affiliation.lower() in full_affiliation:
                    controlled_affiliations.append(affiliations[0])
                    break

        return controlled_affiliations

    def get_contributor_role(self, role_700=None):
        """Return contributor role.

        :param role_700: String, role found in field 700$e
        :returns: String containing the mapped role or None
        """
        if role_700 in ['Dir.', 'Codir.']:
            return 'dgs'

        if role_700 == 'Libr./Impr.':
            return 'prt'

        if role_700 == 'joint author':
            return 'cre'

        if not role_700:
            doc_type = self.blob_record.get('980__', {}).get('a')

            if not doc_type:
                return None

            if doc_type in ['PREPRINT', 'POSTPRINT', 'DISSERTATION', 'REPORT']:
                return 'cre'

            if doc_type in [
                    'BOOK', 'THESIS', 'MAP', 'JOURNAL', 'PARTITION', 'AUDIO',
                    'IMAGE'
            ]:
                return 'ctb'

        return None

    def verify(self, result):
        """Verify record data integrity after processing.

        :param result: Record data
        """

        def is_pa_mandatory():
            """Check if record types make provision activity mandatory."""
            document_type = result.get('documentType')

            if not document_type:
                return True

            if document_type not in [
                    'coar:c_beb9', 'coar:c_6501', 'coar:c_998f',
                    'coar:c_dcae04bc', 'coar:c_3e5a', 'coar:c_5794',
                    'coar:c_6670'
            ]:
                return True

            return False

        self.result_ok = True

        # Check if provision activity is set, but it's optional depending
        # on record types
        if 'provisionActivity' not in result and is_pa_mandatory():
            self.result_ok = False
            current_app.logger.warning(
                'No provision activity found in record {record}'.format(
                    record=result))
