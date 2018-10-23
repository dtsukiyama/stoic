import sqlite3
import pandas as pd
from sqlite3 import Error
from pandas.io import sql


def createConnection(database):
    try:
        conn = sqlite3.connect(database, check_same_thread=False)
        return conn
    except Error as e:
        print(e)

    return None

def createTable(conn, sql):
    try:
        c = conn.cursor()
        c.execute(sql)
    except Error as e:
        print(e)

def modelTable():
    sql =  """CREATE TABLE IF NOT EXISTS model_builds(container_name text NOT NULL,
                                                      repository text NOT NULL, 
                                                      UNIQUE(container_name, repository)); """
    conn = createConnection('database/models.db')
    if conn is not None:
        createTable(conn, sql)
    else:
        print("Error. Cannot create the database connection.") 

    

def createModel(new_index):
    sql = ''' INSERT OR IGNORE INTO model_builds(container_name, repository)
              VALUES(?,?) '''
    conn = sqlite3.connect('database/models.db', check_same_thread=False) 
    conn.execute(sql, new_index)
    conn.commit()
    conn.close()

def deleteModel(container):
    sql = '''Delete from model_builds where container_name=?'''
    conn = createConnection('database/models.db')
    if conn is not None:
        conn.execute(sql,(container,))
    else:
        print("Error. Cannot create the database connection.") 
 

def returnModels():
    # returns list of tuples
    conn = sqlite3.connect('database/models.db', check_same_thread=False)
    query_string = """select * from model_builds"""
    cur = conn.cursor()
    cur.execute(query_string)
    rows = cur.fetchall()
    return rows

