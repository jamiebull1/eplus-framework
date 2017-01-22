# Copyright (c) 2017 Jamie Bull
# =======================================================================
#  Distributed under the MIT License.
#  (See accompanying file LICENSE or copy at
#  http://opensource.org/licenses/MIT)
# =======================================================================
"""pytest for eplus-framework db_lib"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import NoSuchTableError

from framework.manager.src.db_lib import create_table
from framework.manager.src.db_lib import drop_table
from framework.manager.src.db_lib import insert
from framework.manager.src.db_lib import reflect_cols
from framework.manager.src.db_lib import select
from framework.manager.src.jobgenerator import job_specs
from framework.manager.src.jobgenerator import store_params


def test_store_params():
    drop_table('postgis', 'sdb', 'test')
    columns = [('uid', 'VARCHAR'), ('col1', 'VARCHAR'), ('col2', 'NUMERIC')]
    create_table('postgis', 'sdb', 'test', columns, primary_key='uid')
    store_params('postgis', 'sdb', 'test', {'col1': 1, 'col2': '2'})
    result = reflect_cols('postgis', 'sdb', 'test')
    expected = ['col1', 'col2', 'uid']
    assert set(result) == set(expected)

    result = select('postgis', 'sdb', 'test', fields='col1', first=True)
    expected = ('1', )
    assert result == expected
    
    drop_table('postgis', 'sdb', 'test')


def test_insert():
    drop_table('postgis', 'sdb', 'test')
    columns = [('col1', 'VARCHAR'), ('col2', 'NUMERIC')]
    create_table('postgis', 'sdb', 'test', columns)
    insert('postgis', 'sdb', 'test', {'col1': 1, 'col2': 2})
    
    drop_table('postgis', 'sdb', 'test')
    columns = [('col1', 'VARCHAR'), ('col2', 'NUMERIC')]
    create_table('postgis', 'sdb', 'test', columns, primary_key='col1')
    insert('postgis', 'sdb', 'test', {'col1': 1, 'col2': 2})
    try:
        insert('postgis', 'sdb', 'test', {'col1': 1, 'col2': 3})
        assert False
    except IntegrityError:
        pass
    drop_table('postgis', 'sdb', 'test')
    
    
def test_reflect_cols():
    try:
        reflect_cols('postgis', 'sdb', 'nonesuchtable')
        assert False
    except NoSuchTableError:
        pass
    drop_table('postgis', 'sdb', 'test')
    columns = [('col1', 'VARCHAR'), ('col2', 'NUMERIC')]
    create_table('postgis', 'sdb', 'test', columns)
    result = reflect_cols('postgis', 'sdb', 'test')
    expected = ['col1', 'col2']
    assert result == expected
    drop_table('postgis', 'sdb', 'test')

    
def test_job_specs():
    jobs = job_specs()
    jobspec = jobs[0]
    columns = [(key, 'VARCHAR') for key in jobspec]
    create_table('postgis', 'sdb', 'test', columns)
    store_params('postgis', 'sdb', 'test', jobspec)
    drop_table('postgis', 'sdb', 'test')


def test_drop_table():                         
    columns = [('col1', 'VARCHAR'), ('col2', 'NUMERIC')]
    create_table('postgis', 'sdb', 'test', columns)
    drop_table('postgis', 'sdb', 'test')


def test_create_table():
    drop_table('postgis', 'sdb', 'test')
    columns = [('col1', 'VARCHAR'), ('col2', 'NUMERIC')]
    create_table('postgis', 'sdb', 'test', columns, primary_key='col1')
    drop_table('postgis', 'sdb', 'test')
