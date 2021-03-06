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

"""Document extension."""

from __future__ import absolute_import, print_function

import jinja2
from flask_assets import Bundle, Environment
from flask_bootstrap import Bootstrap
from flask_security import user_registered
from flask_wiki import Wiki
from invenio_files_rest.signals import file_deleted, file_uploaded

from sonar.modules.permissions import has_admin_access, has_submitter_access, \
    has_superuser_access
from sonar.modules.receivers import file_deleted_listener, \
    file_uploaded_listener
from sonar.modules.users.api import current_user_record
from sonar.modules.users.signals import user_registered_handler
from sonar.modules.utils import get_specific_theme, get_switch_aai_providers, \
    get_view_code

from . import config


def utility_processor():
    """Dictionary for passing data to templates."""
    return dict(has_submitter_access=has_submitter_access,
                has_admin_access=has_admin_access,
                has_superuser_access=has_superuser_access,
                ui_version=config.SONAR_APP_UI_VERSION,
                aai_providers=get_switch_aai_providers,
                view_code=get_view_code(),
                current_user_record=current_user_record,
                get_specific_theme=get_specific_theme)


class Sonar(object):
    """SONAR extension."""

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

            # Force to load SONAR templates before others
            # it is require for Flask-Security see:
            # https://pythonhosted.org/Flask-Security/customizing.html#emails
            sonar_loader = jinja2.ChoiceLoader(
                [jinja2.PackageLoader('sonar', 'templates'), app.jinja_loader])
            app.jinja_loader = sonar_loader

    def init_app(self, app):
        """Flask application initialization."""
        self.init_config(app)
        app.extensions['sonar_app'] = self

        if app.config['SONAR_APP_ENABLE_CORS']:
            from flask_cors import CORS
            CORS(app)

        Bootstrap(app)
        Wiki(app)

        # Register assets for sonar-ui
        assets = Environment(app)
        assets.register(
            'sonar_ui_js',
            Bundle('sonar-ui/runtime.js',
                   'sonar-ui/polyfills.js',
                   'sonar-ui/main.js',
                   output='sonar_ui.%(version)s.js'))

        app.context_processor(utility_processor)

        # Connect to signal sent when a user is created in Flask-Security.
        user_registered.connect(user_registered_handler, weak=False)

        # Connect to signal sent when a file is uploaded or deleted
        file_uploaded.connect(file_uploaded_listener, weak=False)
        file_deleted.connect(file_deleted_listener, weak=False)

    def init_config(self, app):
        """Initialize configuration."""
        for k in dir(config):
            if k.startswith('SONAR_APP_'):
                app.config.setdefault(k, getattr(config, k))
