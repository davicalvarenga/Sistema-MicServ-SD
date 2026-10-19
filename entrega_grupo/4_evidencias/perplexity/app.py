from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional, List, Dict, Any
import re

app = FastAPI()

# Persistência em memória
users_db: Dict[str, dict] = {}
expenses_db: Dict[str, List[dict]] = {}
tokens_db: Dict[str, str] = {}

security = HTTPBearer()


class UserRegister(BaseModel):
    email: str
    password: str

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Email inválido')
        return v


class UserLogin(BaseModel):
    email: str
    password: str


class ExpenseCreate(BaseModel):
    description: str
    amount: float
    date: str
    category: str

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount deve ser maior que zero')
        return v


class ExpenseResponse(BaseModel):
    id: str
    description: str
    amount: float
    date: str
    category: str


class UserResponse(BaseModel):
    id: str
    email: str


class TokenResponse(BaseModel):
    access_token: str


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    token = credentials.credentials
    if token not in tokens_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )
    return tokens_db[token]


@app.post("/auth/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
def register(user: UserRegister):
    if user.email in users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já cadastrado"
        )
    user_id = str(len(users_db) + 1)
    users_db[user.email] = {
        "id": user_id,
        "email": user.email,
        "password": user.password
    }
    expenses_db[user_id] = []
    return UserResponse(id=user_id, email=user.email)


@app.post("/auth/login", response_model=TokenResponse)
def login(user: UserLogin):
    if user.email not in users_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas"
        )
    stored_user = users_db[user.email]
    if stored_user["password"] != user.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas"
        )
    token = f"token_{stored_user['id']}_{datetime.now().timestamp()}"
    tokens_db[token] = stored_user["id"]
    return TokenResponse(access_token=token)


@app.post("/expenses", status_code=status.HTTP_201_CREATED, response_model=ExpenseResponse)
def create_expense(expense: ExpenseCreate, current_user_id: str = Depends(get_current_user)):
    expense_id = str(len(expenses_db.get(current_user_id, [])) + 1)
    expense_data = {
        "id": expense_id,
        "description": expense.description,
        "amount": expense.amount,
        "date": expense.date,
        "category": expense.category
    }
    if current_user_id not in expenses_db:
        expenses_db[current_user_id] = []
    expenses_db[current_user_id].append(expense_data)
    return ExpenseResponse(**expense_data)


@app.get("/expenses", response_model=List[ExpenseResponse])
def list_expenses(current_user_id: str = Depends(get_current_user)):
    user_expenses = expenses_db.get(current_user_id, [])
    return [ExpenseResponse(**expense) for expense in user_expenses]


@app.get("/expenses/total")
def get_total_expenses(current_user_id: str = Depends(get_current_user)):
    user_expenses = expenses_db.get(current_user_id, [])
    total = sum(expense["amount"] for expense in user_expenses)
    return {"total": total}
