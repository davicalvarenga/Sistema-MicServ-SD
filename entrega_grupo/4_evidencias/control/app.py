from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

users = {}
expenses = []


class User(BaseModel):
    email: str
    password: str


class Expense(BaseModel):
    description: str
    amount: float
    date: str
    category: str


@app.post("/auth/register")
def register(user: User):
    users[user.email] = user.password
    return {"email": user.email, "password": user.password, "message": "registered"}


@app.post("/auth/login")
def login(user: User):
    return {"token": "token-" + user.email}


@app.post("/expenses")
def add_expense(expense: Expense):
    item = {"id": len(expenses) + 1, **expense.dict()}
    expenses.append(item)
    return item


@app.get("/expenses")
def list_expenses():
    return expenses


@app.get("/expenses/total")
def total():
    return {"total": sum(e["amount"] for e in expenses)}
