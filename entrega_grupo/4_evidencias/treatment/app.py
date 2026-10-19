import re
import secrets
from fastapi import FastAPI, Depends, HTTPException, Header
from pydantic import BaseModel

app = FastAPI()

_users = {}          # email -> {"id", "password"}
_tokens = {}         # token -> email
_expenses = {}       # email -> [expense,...]
_seq = {"user": 0, "exp": 0}

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Credentials(BaseModel):
    email: str
    password: str


class ExpenseIn(BaseModel):
    description: str
    amount: float
    date: str
    category: str


def current_user(authorization: str = Header(default="")):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="NAO_AUTORIZADO")
    token = authorization.split(" ", 1)[1]
    email = _tokens.get(token)
    if not email:
        raise HTTPException(status_code=401, detail="NAO_AUTORIZADO")
    return email


@app.post("/auth/register", status_code=201)
def register(body: Credentials):
    if not EMAIL_RE.match(body.email):
        raise HTTPException(status_code=422, detail="FORMATO_INVALIDO")
    if body.email in _users:
        raise HTTPException(status_code=409, detail="JA_EXISTE")
    _seq["user"] += 1
    _users[body.email] = {"id": _seq["user"], "password": body.password}
    _expenses.setdefault(body.email, [])
    return {"id": _seq["user"], "email": body.email}  # senha nunca retornada


@app.post("/auth/login")
def login(body: Credentials):
    u = _users.get(body.email)
    if not u or u["password"] != body.password:
        raise HTTPException(status_code=401, detail="NAO_AUTORIZADO")
    token = secrets.token_hex(16)
    _tokens[token] = body.email
    return {"access_token": token}


@app.post("/expenses", status_code=201)
def create_expense(body: ExpenseIn, email: str = Depends(current_user)):
    if body.amount <= 0:
        raise HTTPException(status_code=422, detail="VALOR_INVALIDO")
    _seq["exp"] += 1
    item = {"id": _seq["exp"], "description": body.description, "amount": body.amount,
            "date": body.date, "category": body.category}
    _expenses.setdefault(email, []).append(item)
    return item


@app.get("/expenses")
def list_expenses(email: str = Depends(current_user)):
    return _expenses.get(email, [])


@app.get("/expenses/total")
def total(email: str = Depends(current_user)):
    return {"total": sum(e["amount"] for e in _expenses.get(email, []))}
