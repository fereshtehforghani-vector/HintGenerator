"""
This file contains the logic for connecting to the Cloud SQL database, initializing the conversation history table, and saving conversation turns (user query + model response) to the database. 
"""

import uuid
import pg8000 # This library allows python to speak to PostgreSQL databases, which is what Cloud SQL uses.
from google.cloud.sql.connector import Connector # simplifies connection between cloud run/function and Cloud SQL

# HARDCODED VALUES FOR TESTING - TODO: Change
DB_USER = "zebra_db_user"
DB_PASS = "TestPass@123" 
DB_NAME = "conversation_history"

# Format: project:region:instance-name
INSTANCE_CONNECTION_NAME = "zebra-ai-assist-poc:us-central1:zebra-robotics-convo-history"

conn = None # This starts off as none, prompting a new connection - but then once made, that new connection instance is stored here 


def get_connection():
    global conn
    try:
        if conn is None:
            raise Exception("No connection")
        conn.run("SELECT 1")
        # Send a tiny test query to the database ("give me the number 1") - this means there is no need to make a new connection
        # This checks if the existing connection is still alive
        # If the database dropped the connection (timeout, restart, etc.) this will throw an error
    except Exception:
        # Create connector inside the function instead of at module level
        connector = Connector() # Create a Cloud SQL connector object (handles secure connection to Cloud SQL)
        conn = connector.connect(
            INSTANCE_CONNECTION_NAME,
            "pg8000",
            user=DB_USER,
            password=DB_PASS,
            db=DB_NAME,
        )
    return conn


# This function creates the conversation_history table if it does not already exist.
def init_db():
    connection = get_connection()
    cursor = connection.cursor() # Cursor object allows us to execute SQL queries
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS conversation_history (
            id TEXT PRIMARY KEY,
            conversation_id TEXT,
            user_query TEXT NOT NULL,
            model_response TEXT NOT NULL,
            image_url TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
    )
    connection.commit()
    cursor.close()


# This function stores one user turn and one model turn together as a single row in the conversation history table.
def save_conversation_turn(conversation_id: str, user_query: str, model_response: str, image_url: str = None):
    init_db()
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO conversation_history (id, conversation_id, user_query, model_response, image_url)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (str(uuid.uuid4()), conversation_id, user_query, model_response, image_url)
    )
    connection.commit()
    cursor.close()


