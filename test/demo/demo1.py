import asyncio
import time
from enum import Enum
from typing import Optional
from fastapi import status
from fastapi import FastAPI, Query, Form, status
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse, StreamingResponse

app = FastAPI(title="启动项目"
              , description="启动项目01"
              , version="0.1.0")

async def number_stream():
    for i in range(5):
        yield f"data: chunk {i}\n\n"
        await asyncio.sleep(0.3)

@app.get("/stream")
def stream():
    return StreamingResponse(number_stream(), media_type="text/event-stream")


class UserIn(BaseModel):
    username: str = Field(default="root", description="用户名")
    password: str = "123456"

class UserOut(BaseModel):
    username: str = Field(description="用户名")

@app.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(user: UserIn):
    return {"username": user.username}


@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    return {"username": username, "received_password_len": len(password)}

class Person(BaseModel):
    name: str = Field(description="姓名")
    age: int = Field(description="年龄")

@app.post("/query_person")
def query_person(person: Person):
    return {"person": person}

@app.get("/")
async def say_hello(name: Optional[str] = "World"):
    return JSONResponse(status_code=403,
                        content={"message": f"Hello, {name}!"})

@app.get("/sleep")
async def sleep():
    time.sleep(10)
    return {"message": "Awake!"}

@app.get("/query/{name}")
def query(name: str):
    return {"name": name}

class Size(str, Enum):
    small = "small"
    medium = "medium"
    large = "large"

@app.get("/cups/{size}")
def get_cup(size: Size):
    return {"size": size, "ml": {"small": 250, "medium": 400, "large": 600}[size]}

@app.get("/query_age")
def query_age(age: int = Query(ge=1, le=120, description="年龄，1-120岁")):
    return {"age": age}
