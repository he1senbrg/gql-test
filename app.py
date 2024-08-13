from flask import Flask, jsonify, request, g
import strawberry
from strawberry.flask.views import GraphQLView
from typing import List
from databases import Database
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Date

DATABASE_URL = "sqlite:///./test.db"
database = Database(DATABASE_URL)
metadata = MetaData()

# Define tables
members = Table(
    "members",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String),
    Column("MAC", String)
)

attendances = Table(
    "attendances",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("member_id", Integer),
    Column("date", Date),
)

# Create the database
engine = create_engine(DATABASE_URL)
metadata.create_all(engine)

# GraphQL types
@strawberry.type
class Member:
    id: int
    name: str
    MAC: str

@strawberry.type
class Attendance:
    id: int
    member_id: int
    date: str

SECRET_KEY = "your_secret_key"

@strawberry.type
class Query:
    @strawberry.field
    def members(self) -> List[Member]:
        query = members.select()
        result = database.fetch_all(query)
        return [Member(**dict(row)) for row in result]

    @strawberry.field
    def attendances(self) -> List[Attendance]:
        query = attendances.select()
        result = database.fetch_all(query)
        return [Attendance(**dict(row)) for row in result]

@strawberry.type
class Mutation:
    @strawberry.mutation
    def add_member(self, name: str, MAC: str) -> Member:
        query = members.insert().values(name=name, MAC=MAC)
        last_record_id = database.execute(query)
        return Member(id=last_record_id, name=name, MAC=MAC)

    @strawberry.mutation
    def mark_attendance(self, mac_list: List[str], secret_key: str, date: str) -> Attendance:
        if secret_key != SECRET_KEY:
            raise Exception("Invalid secret key")

        query = members.select().where(members.c.MAC.in_(mac_list))
        results = database.fetch_all(query)
        member_ids = [row["id"] for row in results]

        if not member_ids:
            raise Exception("No matching members found")

        # Insert attendance logs
        query = attendances.insert().values(member_id=member_ids[0], date=date)
        last_record_id = database.execute(query)
        
        return Attendance(id=last_record_id, member_id=member_ids[0], date=date)

# Create the schema
schema = strawberry.Schema(Query, Mutation)

# Create the Flask app
app = Flask(__name__)

# Add the GraphQL endpoint
app.add_url_rule(
    "/graphql",
    view_func=GraphQLView.as_view("graphql_view", schema=schema)
)

# Add a simple route
@app.route("/")
def hello():
    return "My Flask API !!"

# Startup and cleanup database connections
@app.before_request
def connect_db():
    if not hasattr(g, 'db'):
        database.connect()

@app.teardown_appcontext
def disconnect_db(exception=None):
    if hasattr(g, 'db'):
        database.disconnect()

# Run the app
if __name__ == "__main__":
    app.run()
