"""
db_lib.py
~~~~~~~~~
Interface with a database.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import ConfigParser
import os

from sqlalchemy import MetaData, Table, Column
import sqlalchemy.engine
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError


THIS_DIR = os.path.abspath(os.path.dirname(__file__))
URL = "{driver}://{user}:{password}@localhost/{database}"

engines = {}
metadatas = {}
tablepattern = "{db}.{schema}.{table}"
config = ConfigParser.ConfigParser()
config.readfp(open(os.path.join(THIS_DIR, os.pardir, 'config', 'client.cfg')))
sessions = {}

params = {
    'driver': config.get('ResultsDB', 'driver'),
    'database': config.get('ResultsDB', 'database'),
    'user': config.get('ResultsDB', 'user'),
    'password': config.get('ResultsDB', 'password'),
          }


def get_engine(dbname, reuse=True):
    """Provide engine with connection set to given db.
    
    Parameters
    ----------
    dbname : str
        name of database to which to connect.
        
    Returns
    -------
    SQLAlchemy Engine object
    
    """
    if not reuse or dbname not in engines:
        driver = params['driver']
        user = params['user']
        password = params['password']
        database = params['database']
        engines[dbname] = sqlalchemy.create_engine(
            URL.format(**locals()), echo=True)
    return engines[dbname]


def create_table(db, schema, table, columns, primary_key=""):
    """Create a new table in the database.

    Parameters
    ----------
    db : str
        Name of database to which to connect.
    schema : str
        Name of schema to which the database belongs.
    table : str
        Name of database table to create.
    columns : list of tuples
        Details of the table columns.
    primary_key : str, optional
        Column to be set as the primary key.

    """
    engine = get_engine(db)
    tablename = tablepattern.format(**locals())
    columns = ', '.join([' '.join(c) for c in columns])
    if primary_key:
        primary_key = ", PRIMARY KEY ({primary_key})".format(**locals())
    sql = "CREATE TABLE {tablename} ({columns}{primary_key})".format(**locals())
    with engine.begin() as con:
        con.execute(sql)


def drop_table(db, schema, table):
    """Completely remove a table from the database.

    Parameters
    ----------
    db : str
        Name of database to which to connect.
    schema : str
        Name of schema to which the database belongs.
    table : str
        Name of database table to be dropped.

    """
    engine = get_engine(db)
    tablename = tablepattern.format(**locals())
    sql = """DROP TABLE IF EXISTS {tablename}""".format(**locals())
    with engine.begin() as con:
        con.execute(sql)


def insert(db, schema, table, data):
    """Insert data into an existing table.
    
    Parameters
    ----------
    db : str
        Name of database to which to connect.
    schema : str
        Name of schema to which the database belongs.
    table : str
        Name of database table to be dropped.
    data : 
        The data to be inserted, as a dict in the form {'col': value, ...}.
        
    """
    engine = get_engine(db)
    tablename = tablepattern.format(**locals())
    columns = []
    values = []
    for column, value in data.items():
        columns.append(column)
        values.append("'%s'" % str(value))
    columns = ', '.join(columns)
    values = ', '.join(values)
    sql = """INSERT INTO {tablename} ({columns}) VALUES ({values})
          """.format(**locals())
    with engine.begin() as con:
        con.execute(sql)


def insert_from_csv(db, schema, table, csvfile):
    """Insert the contents of a CSV file into an existing table.
    """
    engine = get_engine(db)
    tablename = tablepattern.format(**locals())
    sql = """COPY {tablename} FROM '{csvfile}' DELIMITERS ',' CSV HEADER
          """.format(**locals())
    with engine.begin() as con:
        con.execute(sql)
    

def truncate(db, schema, table):
    """Quickly remove all data from a table in the database.
    """
    engine = get_engine(db)
    tablename = tablepattern.format(**locals())
    sql = "TRUNCATE {tablename}".format(**locals())
    with engine.begin() as con:
        con.execute(sql)


def runsql(db, sql, first=False, fetchall=False):    
    """Run any valid SQL textual string data in database.
    
    Parameters
    ----------
    db : str
        name of database to which to connect.
    sql : str
        Any valid SQL textual string.
    first : boolean, optional
        If true, only fetch the first row of the result set.        
    fetchall : boolean, optional
        If true, fetch all rows of the result set.        

    """
    engine = get_engine(db)
    with engine.begin() as con:
        if first:
            return con.execute(sql).first()
        elif fetchall:
            return con.execute(sql).fetchall()
        else:
            return con.execute(sql)


def select(db, schema, table, fields=None, where=None, group=None, 
           order=None, distinct=False, first=False, limit=None):
    """PostGIS dialect SELECT query builder.
    """
    engine = get_engine(db)
    tablename = tablepattern.format(**locals())
    fields = "{fields}".format(**locals()) if fields else '*'
    distinct = "DISTINCT " if distinct else ''
    select = "SELECT {distinct}{fields} FROM {tablename}".format(**locals())
    where = "WHERE {where}".format(**locals()) if where else ''
    group = "GROUP BY {group}".format(**locals()) if group else ''    
    order = "ORDER BY {order}".format(**locals()) if order else ''
    limit = "LIMIT {limit}".format(**locals()) if limit else ''
    sql = "{select} {where} {group} {order} {limit}".format(**locals())
    with engine.begin() as con:
        if first:
            return con.execute(sql).first()
        else:
            return con.execute(sql).fetchall()


def reflect_cols(db, schema, tblname, key='name'):
    """List names of all field in the database table.
    
    Parameters
    ----------
    db : str
        Name of database to which to connect.
    schema : str
        Name of schema to which the database belongs.
    tblname : str
        Name of database table to be reflected.
    key : str
        Element to reflect from the table definition.
        
    Returns
    -------
    list
        List of field names.
    
    """
    engine = get_engine(db)
    insp = sqlalchemy.engine.reflection.Inspector.from_engine(engine)
    return [col[key] for col in insp.get_columns(tblname, schema)]


def move_schema(db, schema, new_schema, table):
    """Move a table from one schema to another.
    """
    engine = get_engine(db)
    tablename = tablepattern.format(**locals())    
    sql = "ALTER TABLE {tablename} SET SCHEMA {new_schema}".format(**locals())
    with engine.begin() as con:
        con.execute(sql)
