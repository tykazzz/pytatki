import pytest
import pymysql
from pytatki.dbconnect import connection, create_user, create_status, create_usergroup, add_user_to_usergroup, create_notegroup, create_note_type, create_note
from passlib.hash import sha256_crypt
from pytatki.views import has_access_to_note
from init_db import parse_sql, db_init


@pytest.fixture(autouse=True)
def create_db():
    conn = pymysql.connect(host='127.0.0.1', user='root',
                           charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
    cursor = conn.cursor()
    cursor.execute("SHOW DATABASES LIKE \'pytatki\'")
    db_exists = cursor.fetchone()
    if db_exists:
        raise Warning("Database exists")
    for query in parse_sql('sql/create-database.sql'):
        cursor.execute(query)
    conn.close()

@pytest.fixture(autouse=True)
def insert_status(create_db):
    _, conn = connection()
    conn.begin()
    create_status(conn, 'active', 'Record is active')
    conn.commit()
    _.close()
    conn.close()

@pytest.fixture(autouse=True)
def insert_user(insert_status):
    _, conn = connection()
    conn.begin()
    user_id = create_user(conn, 'test', 'test', 'test@test', 1)
    conn.commit()
    _.close()
    conn.close()
    return user_id

@pytest.fixture(autouse=True)
def insert_usergroup(insert_user):
    _, conn = connection()
    conn.begin()
    usergroup_id = create_usergroup(conn, 'test', 'test')
    add_user_to_usergroup(conn, insert_user, usergroup_id)
    conn.commit()
    _.close()
    conn.close()
    return usergroup_id

@pytest.fixture(autouse=True)
def insert_notegroup(insert_usergroup, insert_user):
    _, conn = connection()
    conn.begin()
    notegroup_id = create_notegroup(conn, 'test', insert_usergroup)
    conn.commit()
    _.close()
    conn.close()
    return notegroup_id

@pytest.fixture(autouse=True)
def insert_text_note_type(create_db):
    _, conn = connection()
    conn.begin()
    note_type_id = create_note_type(conn, 'text', 'Text')
    conn.commit()
    _.close()
    conn.close()
    return note_type_id

@pytest.fixture(scope='function', autouse=True)
def insert_note(insert_user, insert_text_note_type, insert_notegroup):
    """Insert new note"""
    con, conn = connection()
    conn.begin()
    note_id = create_note(conn, 'test', 'Test', insert_text_note_type, insert_user, insert_notegroup)
    conn.commit()
    con.close()
    conn.close()

def test_user_has_access_to_note(insert_note):
    if has_access_to_note(1, 1) != True:
        raise AssertionError()
