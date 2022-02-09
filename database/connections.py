import psycopg2
import os
from psycopg2.extras import NamedTupleCursor
from requests import api

accountId = os.environ.get('accountId', "Not set")

class DbConnection:
    """
        This class will create a single connection to Database. It will also ensure only one instance of Dbconnection class exists.
        Arguments:
            username - [string] -- username for connecting to Database.
            password - [string] -- Database pasword for connection to server.
            host - [string] -- The host  for the PostgreSQL server.
            database - [string] -- Name of the database to which we will be connecting.
            port - [integer] -- Port for Database,. Standard port for postgresql is 5432.
            
        Methods:
            connection - [ normal method ] -- Will create a conn attribute. which is a connection to database.
            get_instance - [ static method ] -- This method will return an object already created or create a new object incase class has no instances created.
    """
    __instance__ = None
    
    def __init__(self, username, password, host, database, port ):
        self.username = username
        self.password = password
        self.host = host
        self.database = database
        self.port = port
        self.connection_exception = False
        
        if DbConnection.__instance__ is None:
            DbConnection.__instance__ = self
        else:
            DbConnection.get_instance()
        
    def connection(self):
        try:
                
            self.conn = psycopg2.connect(
                host=self.host, port= self.port, user=self.username, password=self.password, database= self.database, # sslmode="require"
            )
            print(dir(self.conn))
        except Exception as e:
            self.connection_exception = True
            print(f"{accountId} DB Connection Error {e}")
        
    def __enter__(self):
        print(f" {accountId} DB Connection Started")
        self.connection()
        if self.connection_exception:
            return None
        return self.conn
    
    @staticmethod
    def get_instance():
        if not DbConnection.__instance__:
            DbConnection(DbConnection.username, DbConnection.password, DbConnection.host, DbConnection.database, DbConnection.port)
        return DbConnection.__instance__
    
    def __exit__(self, *exc):
        print(f"{accountId} DB Connection Exited")
        try:
            self.conn.close()
        except Exception as e:
            print(f"{accountId} Error Occurred {e}")
        

with DbConnection(username, password, host, database, port) as db_connection:
    if db_connection is None:
        print(f"{accountId} There was an error connecting with the database")
    else:
        cursor = db_connection.cursor(cursor_factory=NamedTupleCursor)
        sql_query = """SELECT <apikey> FROM <table WHERE <accountId> = '{}'""".format(accountId)
        cursor.execute(sql_query)
        rows = cursor.fetchone()
        api_key = rows.provisioningkey
        print(api_key) # This will return the API key for the account to be used for Cloud SDKs.