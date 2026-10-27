from novel_studio_api import Studio
import json
studio=Studio.connect()
project=studio.projects.current()
chapters=studio.chapters.list(limit=100)
print(json.dumps({"project":project,"chapters":chapters},ensure_ascii=False,indent=2))
