#! /usr/bin/python

import os
from datetime import datetime
import sqlite3
from collections import namedtuple

from . import log

INSTALL_FIELDS = ['source', 'version', 'timestamp']
_Install = namedtuple('Install', INSTALL_FIELDS)

def _row_factory(cursor, row):
    return _Install(*row)


class BuildHistory(object):

    def __init__(self, db_path=None):
        if db_path is None:
            import addon
            db_path = addon.data_path
        self.db_file = os.path.join(db_path, 'builds.db')

    @log.with_logging("Added install {}|{} to database",
                      "Failed to add install {}|{} to database")
    def add_install(self, source, build):
        self._create_database()
        with sqlite3.connect(self.db_file) as conn:
            conn.execute('''INSERT OR IGNORE INTO builds (source, version)
                            VALUES (?, ?)''', (source, build.version))

            build_id = conn.execute('''SELECT last_insert_rowid()
                                       FROM builds''').fetchone()[0]
            if build_id == 0:
                build_id = self._build_id(source, build.version)

            conn.execute('''INSERT INTO installs (build_id, timestamp)
                            VALUES (?, ?)''', (build_id, datetime.now()))

    @log.with_logging("Retrieved full install history",
                      "Failed to retrieve full install history")
    def full_install_history(self):
        with sqlite3.connect(self.db_file, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
            conn.row_factory = _row_factory
            return conn.execute('''SELECT {}
                                   FROM installs
                                   JOIN builds ON builds.id = build_id
                                   ORDER BY timestamp DESC'''
                                .format(','.join(INSTALL_FIELDS))).fetchall()

    def is_previously_installed(self, source, build):
        with sqlite3.connect(self.db_file) as conn:
            return bool(conn.execute('''SELECT COUNT(*) FROM installs WHERE
                                        source = ? AND version = ?''',
                                     (source, build.version)).fetchone()[0])

    def _create_database(self):
        with sqlite3.connect(self.db_file) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS builds
                            (id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT NOT NULL,
                             version TEXT NOT NULL, marked INTEGER default 0, comments TEXT,
                             UNIQUE(source, version))''')

            conn.execute('''CREATE UNIQUE INDEX IF NOT EXISTS source_version
                            ON builds (source, version)''')

            conn.execute('''CREATE TABLE IF NOT EXISTS installs
                            (id INTEGER PRIMARY KEY AUTOINCREMENT,
                             build_id INTEGER REFERENCES builds(id),
                             timestamp TIMESTAMP NOT NULL)''')

    def _build_id(self, source, version):
        with sqlite3.connect(self.db_file) as conn:
            return conn.execute('''SELECT id FROM builds WHERE source = ? AND version = ?''',
                                (source, version)).fetchone()[0]

    def __str__(self):
        return '\n'.join("{:16s}  {:>7s}  {:30s}".format(
            install.timestamp.strftime("%Y-%m-%d %H:%M"), install.version, install.source)
            for install in reversed(self.full_install_history()))
