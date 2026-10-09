import json

from fastapi import FastAPI
from fastapi.responses import FileResponse

import db

app = FastAPI()
db.init()


@app.get("/api/items")
def items():
    out = []
    for it in db.all_items():
        it["messages"] = db.get_messages(json.loads(it["source_ids"]))
        out.append(it)
    return out


@app.get("/")
def index():
    return FileResponse("static/index.html")