"""Actual Director/ReviewCenter with bounded fake model responses; never real-AI evidence."""
import asyncio,json
import pytest
from app.creative.director import Patch,Review,Rewrite,Candidate
from app.library.storage import read,write
from app.studio_tools import text_hash,utf16_index
from test_creative_director import lab,new,body,done,fake,Fake

async def reviewed(lab,monkeypatch,text="🌧️候选里的对白。"):
    class Reviewer(Fake):
        def start_task(self,prompt,emit,**kw):
            return {"status":"completed","output":json.dumps({"verdict":"WARN","summary":"Synthetic report only","issues":[{"severity":"minor","message":"Synthetic finding","evidence":[text,"ABSENT_QUOTE"],"priority":"SUGGESTION","confidence":"HIGH"}]},ensure_ascii=False)}
    monkeypatch.setattr("app.creative.reviews.adapter",lambda *a,**kw:Reviewer(""))
    s,p,*_=lab;row=new(lab);row=s.patch(p,row["id"],Patch(etag=row["etag"],draft=text))
    result=s.review(p,row["id"],Review(etag=row["etag"]));await s.manager(p).get(result["task"]["id"]).runner
    return s.get(p,row["id"])

def test_ai_append_invalidates_saved_review(lab,monkeypatch):
    async def run():
        s,p,pr,path,*_=lab;row=await reviewed(lab,monkeypatch);original=(pr/path).read_bytes();report=s.reviews.path(p,row["review_id"]).read_bytes()
        calls=fake(monkeypatch);after=await done(s,p,await s.control(p,row["id"],body(row,"run")))
        assert after["draft"]!=row["draft"] and len(calls)==1
        assert after.get("review_stale") is True
        assert after["review_validity"]["status"]=="HISTORICAL"
        assert s.reviews.path(p,row["review_id"]).read_bytes()==report and (pr/path).read_bytes()==original
    asyncio.run(run())

def test_ai_rewrite_invalidates_saved_review(lab,monkeypatch):
    async def run():
        s,p,*_=lab;row=await reviewed(lab,monkeypatch);quote="候选";start=utf16_index(row["draft"],row["draft"].index(quote))
        row=s.rewrite(p,row["id"],Rewrite(etag=row["etag"],start=start,end=start+len(quote),quote=quote,instruction="改写这一处"))
        fake(monkeypatch);after=await done(s,p,await s.control(p,row["id"],body(row,"run")))
        assert after["draft"]!=row["draft"] and after.get("review_stale") is True
        assert after["review_validity"]["status"]=="HISTORICAL"
    asyncio.run(run())

def test_restart_retained_output_invalidates_report(lab,monkeypatch):
    async def run():
        s,p,*_=lab;row=await reviewed(lab,monkeypatch);row.update(active_task="gone",status="GENERATING",partial="已收到的追加段落。",active_step=0)
        s.put(p,row);after=s.get(p,row["id"])
        assert after["draft"].endswith("已收到的追加段落。") and after.get("review_stale") is True
        assert after["review_validity"]["status"]=="HISTORICAL"
        persisted=read(s.path(p,row["id"]));assert persisted["review_stale"] and "review_validity" not in persisted
    asyncio.run(run())

def test_old_record_hash_detects_mismatch_without_migration(lab,monkeypatch):
    async def run():
        s,p,*_=lab;row=await reviewed(lab,monkeypatch);path=s.path(p,row["id"]);old=read(path);old.update(draft="旧版漏标的改文。",review_stale=False);write(path,old);before=path.read_bytes()
        result=s.get(p,row["id"]);assert result["review_validity"]["status"]=="HISTORICAL"
        assert path.read_bytes()==before
    asyncio.run(run())

def test_missing_or_corrupt_report_does_not_break_draft(lab,monkeypatch):
    async def run():
        s,p,*_=lab;row=await reviewed(lab,monkeypatch);path=s.reviews.path(p,row["review_id"]);path.write_text("{broken",encoding="utf8")
        bad=s.get(p,row["id"]);assert bad["review_validity"]["status"]=="UNVERIFIED" and bad["draft"]==row["draft"]
        path.unlink();missing=s.get(p,row["id"]);assert missing["review_validity"]["status"]=="UNVERIFIED"
        assert s.history(p)[0]["id"]==row["id"]
    asyncio.run(run())

def test_matching_hash_and_unrelated_settings_do_not_invalidate(lab,monkeypatch):
    async def run():
        s,p,*_=lab;row=await reviewed(lab,monkeypatch);assert row["review_validity"]["status"]=="MATCHES_CANDIDATE"
        report=read(s.reviews.path(p,row["review_id"]));assert report["candidate_sha256"]==text_hash(row["draft"])
        row=s.patch(p,row["id"],Patch(etag=row["etag"],limits=row["limits"]))
        assert row["review_validity"]["status"]=="MATCHES_CANDIDATE"
        report.pop("candidate_sha256");write(s.reviews.path(p,row["review_id"]),report)
        assert s.get(p,row["id"])["review_validity"]["status"]=="UNVERIFIED"
    asyncio.run(run())

def test_review_basis_changes_cannot_clear_historical_flag(lab,monkeypatch):
    async def run():
        s,p,*_=lab;row=await reviewed(lab,monkeypatch);row=s.patch(p,row["id"],Patch(etag=row["etag"],goal="新目标与旧报告条件不同"))
        assert row.get("review_stale") is True and row["review_validity"]["status"]=="HISTORICAL"
        row["review_stale"]=False;s.put(p,row)
        assert s.get(p,row["id"])["review_validity"]["status"]=="HISTORICAL"
    asyncio.run(run())


def test_new_review_resets_stale_but_retains_old_report(lab,monkeypatch):
    async def run():
        s,p,*_=lab;row=await reviewed(lab,monkeypatch);old=s.reviews.path(p,row["review_id"]);original=old.read_bytes()
        row=s.patch(p,row["id"],Patch(etag=row["etag"],draft="作者的新候选。"));assert row["review_stale"]
        result=s.review(p,row["id"],Review(etag=row["etag"]));await s.manager(p).get(result["task"]["id"]).runner
        current=s.get(p,row["id"]);assert not current["review_stale"] and current["review_validity"]["status"]=="MATCHES_CANDIDATE"
        assert current["review_id"]!=row["review_id"] and old.read_bytes()==original
    asyncio.run(run())

@pytest.mark.parametrize("key,value",[("source_path","chapters/other.txt"),("project_id","novel_"+"0"*32),("source_kind","MANUSCRIPT")])
def test_report_provenance_mismatch_is_unverified(lab,monkeypatch,key,value):
    async def run():
        s,p,*_=lab;row=await reviewed(lab,monkeypatch);path=s.reviews.path(p,row["review_id"]);report=read(path);report[key]=value;write(path,report)
        assert s.get(p,row["id"])["review_validity"]["status"]=="UNVERIFIED"
    asyncio.run(run())

def test_cancel_retains_new_text_and_invalidates_previous_review(lab,monkeypatch):
    async def run():
        s,p,*_=lab;row=await reviewed(lab,monkeypatch);fake(monkeypatch,True);running=await s.control(p,row["id"],body(row,"run"))
        for _ in range(100):
            await asyncio.sleep(.02)
            current=s.get(p,row["id"])
            if current.get("partial"):break
        assert current.get("partial")
        stopped=await s.control(p,row["id"],body(current,"interrupt"));await s.manager(p).get(running["active_task"]).runner
        after=s.get(p,row["id"]);assert after["draft"].startswith(row["draft"]) and after["draft"]!=row["draft"]
        assert after["review_stale"] and after["review_validity"]["status"]=="HISTORICAL" and not after["active_task"]
    asyncio.run(run())
