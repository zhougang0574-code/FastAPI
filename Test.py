import time
from typing import Annotated
from fastapi import Depends, BackgroundTasks
from fastapi import FastAPI, HTTPException, Request

app = FastAPI(title="依赖注入")

def send_message(message:str):
    print(f"这里是发送邮件{message}")

@app.get("/query")
def query(name:str,task:BackgroundTasks):
    task.add_task(send_message,name)
    return {"result":"调用成功"}
