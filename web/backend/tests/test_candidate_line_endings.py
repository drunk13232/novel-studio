"""Explicit author adoption in temporary projects; no remote AI or source migration."""
import pytest
from test_creative_director import lab
from app.studio_tools import normalized,utf16_index,Decision
from app.errors import ConsoleError

@pytest.mark.parametrize("eol",["\n","\r\n"])
@pytest.mark.parametrize("replacement_eol",["\n","\r\n","\r","\r\n\n"])
@pytest.mark.parametrize("bom",[False,True])
def test_author_adoption_preserves_document_eol_bom_and_undo_snapshot(lab,eol,replacement_eol,bom):
    s,p,root,path,*_=lab;t=s.tools;file=root/path;raw=eol.join(["开头。","原段。","尾句。",""]);prefix=b"\xef\xbb\xbf" if bom else b"";original=prefix+raw.encode();file.write_bytes(original)
    doc=t.doc(p,path);text=normalized(doc);start=utf16_index(text,text.index("原段。"));replacement="🌧️改写。"+replacement_eol+"下一句。"
    row=t.stage_replacement(p,path,doc["etag"],start,start+len("原段。"),"原段。",replacement,{"kind":"ISOLATED_FORMAT_TEST"})
    assert file.read_bytes()==original
    result=t.decide(p,row["id"],Decision(action="accept",originalHash=row["originalHash"],candidate=row["candidate"]))
    expected=prefix+eol.join(["开头。","🌧️改写。",*( [""] if replacement_eol=="\r\n\n" else [] ),"下一句。","尾句。",""]).encode()
    assert file.read_bytes()==expected
    assert result["file"]["line_ending"]==doc["line_ending"] and result["file"]["editable"]
    retained=t.candidate(p,row["id"]);assert retained["candidate"]==replacement and retained["accepted_text"]==replacement
    revision=root/"history/revisions"/retained["pre_revision"]/"content.txt";assert revision.read_bytes()==original


def test_existing_mixed_source_remains_guarded_without_write(lab):
    s,p,root,path,*_=lab;t=s.tools;file=root/path;original="开头。\r\n原段。\n尾句。".encode();file.write_bytes(original);doc=t.doc(p,path);assert doc["line_ending"]=="MIXED";text=normalized(doc);start=utf16_index(text,text.index("原段。"));row=t.stage_replacement(p,path,doc["etag"],start,start+len("原段。"),"原段。","替换。",{"kind":"ISOLATED_FORMAT_TEST"})
    with pytest.raises(ConsoleError):t.decide(p,row["id"],Decision(action="accept",originalHash=row["originalHash"],candidate=row["candidate"]))
    assert file.read_bytes()==original and t.candidate(p,row["id"])["status"]=="PROPOSED"


@pytest.mark.parametrize("accepted,expected",[("首段。\n尾段。",True),("首段。\r尾段。",True),("首段。\n不同内容。",False),("首段。\n尾段。\n",False)])
def test_director_adoption_receipt_ignores_only_eol_representation(lab,accepted,expected):
    from test_creative_director import new
    from app.creative.director import Patch,Candidate
    s,p,*_=lab;row=new(lab);row=s.patch(p,row["id"],Patch(etag=row["etag"],draft="首段。\r\n尾段。"));staged=s.stage(p,row["id"],Candidate(etag=row["etag"]));c=staged["candidate"]
    s.tools.decide(p,c["id"],Decision(action="accept",originalHash=c["originalHash"],candidate=accepted))
    delivery=s.get(p,row["id"])["delivery"];assert delivery["candidate_status"]=="ACCEPTED" and delivery["candidate_matches_current_draft"]
    assert delivery["author_adopted"] is expected
