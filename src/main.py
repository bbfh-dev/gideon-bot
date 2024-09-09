import json
import os

from bot import BOT, Database


if __name__ == "__main__":
    with open(os.path.join("..", "database.json"), "r") as fp:
        database = json.load(fp)
    BOT.db = Database(database)
    BOT.db.save()
    BOT.run(database.get("token"))
