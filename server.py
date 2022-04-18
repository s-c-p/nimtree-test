from parse import main

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class XMLString(BaseModel):
    xmls: str

@app.post("parse")
def index(xmlstring: XMLString):
    try:
        fn, size = main(xmlstring.xmls)
    except Exception as e:
        return {
            "statusCode": 501,
            "error": str(e)
        }
    else:
        return {
            "statusCode": 200,
            "data": {
                "outputFileName": fn,
                "outputFileSize": size
            }
        }

