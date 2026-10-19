from fastapi import FastAPI, Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List
import uuid

app = FastAPI()

users_db = {}
tokens_db = {}
expenses_db = {}

security = HTTPBearer()


class RegisterIn(BaseModel):
    email: str
    password: str


class RegisterOut(BaseModel):
    id: str
    email: str


class LoginIn(BaseModel):
    email: str
    password: str


class ExpenseIn(BaseModel):
    description: str
    amount: float
    date: str
    category: str


class ExpenseOut(BaseModel):
    id: str
    description: str
    amount: float
    date: str
    category: str


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    if token not in tokens_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing token"
        )
    return tokens_db[token]


@app.post("/auth/register", status_code=status.HTTP_201_CREATED, response_model=RegisterOut)
def register(user: RegisterIn):
    if "@" not in user.email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid email format"
        )
    user_id = str(uuid.uuid4())
    users_db[user_id] = {
        "id": user_id,
        "email": user.email,
        "password": user.password
    }
    return {"id": user_id, "email": user.email}


@app.post("/auth/login", status_code=status.HTTP_200_OK)
def login(user: LoginIn):
    for uid, udata in users_db.items():
        if udata["email"] == user.email and udata["password"] == user.password:
            token = str(uuid.uuid4())
            tokens_db[token] = uid
            return {"access_token": token}
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials"
    )


@app.post("/expenses", status_code=status.HTTP_201_CREATED, response_model=ExpenseOut)
def create_expense(expense: ExpenseIn, user_id: str = Depends(get_current_user_id)):
    if expense.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Amount must be greater than 0"
        )

    exp_id = str(uuid.uuid4())
    exp_data = {
        "id": exp_id,
        "description": expense.description,
        "amount": expense.amount,
        "date": expense.date,
        "category": expense.category
    }

    if user_id not in expenses_db:
        expenses_db[user_id] = []
    expenses_db[user_id].append(exp_data)

    return exp_data


@app.get("/expenses", status_code=status.HTTP_200_OK, response_model=List[ExpenseOut])
def get_expenses(user_id: str = Depends(get_current_user_id)):
    return expenses_db.get(user_id, [])


@app.get("/expenses/total", status_code=status.HTTP_200_OK)
def get_expenses_total(user_id: str = Depends(get_current_user_id)):
    user_expenses = expenses_db.get(user_id, [])
    total = sum(exp["amount"] for exp in user_expenses)
    return {"total": total}
