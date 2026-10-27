"""Allowlisted native audit entry used by the existing chapter workflow."""
import argparse
import json
import sys
import threading
from pathlib import Path

ENGINE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ENGINE/'web/backend'))
from app.errors import ConsoleError
from app.projects.service import NovelWorkspace
from app.domain.characters import CharacterService
from app.domain.planning import Planning
from app.integrations.research import SpecialistRequest
from app.integrations.story import StoryValidator
from app.integrations.stack import STORY_COMMANDS

class ActiveRegistry:
    def __init__(self, root):
        self.engine=ENGINE;self.active=NovelWorkspace(root);self.lock=threading.RLock()
    def workspace(self, id):
        if id!=self.active.root.name:raise ConsoleError('只允许 ACTIVE PROJECT',403)
        return self.active
    def get(self, id):return self.workspace(id).yaml_file('project.yaml')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',required=True,type=Path)
    parser.add_argument('--command',required=True,choices=sorted(STORY_COMMANDS))
    parser.add_argument('--chapter',type=int)
    parser.add_argument('--chapter-id')
    parser.add_argument('--character-id')
    parser.add_argument('--name',action='append',default=[])
    args=parser.parse_args();root=args.root.resolve()
    if root.parent!=ENGINE/'projects' or root.is_symlink() or root.is_junction():
        parser.error('--root 必须是明确选择的本引擎小说目录')
    registry=ActiveRegistry(root);characters=CharacterService(registry);planning=Planning(registry,characters,None)
    request=SpecialistRequest(type='story_'+args.command,chapter=args.chapter,chapter_id=args.chapter_id,character_id=args.character_id,names=args.name)
    result=StoryValidator(ENGINE,registry,characters,planning,root/'metadata/story-validation').run(root.name,request,args.command,lambda *a:None,lambda:False)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
