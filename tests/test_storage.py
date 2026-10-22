from app.storage import Store


def test_store_roundtrip_idempotent(tmp_path):
    store = Store(tmp_path)
    store.add_job("job1", "scrape", {"url":"https://example.org"}, 1)
    page = {"metadata": {"sourceURL":"https://example.org", "title":"Sample"},
            "markdown":"# Example", "html":"<b>Example</b>", "links": ["https://example.org/about"]}
    store.add_page("job1", page)
    store.add_page("job1", page)
    store.update("job1", status="completed", completed=1)
    assert store.list_jobs()[0]["page_count"] == 1
    assert store.job("job1")["status"] == "completed"
    assert store.pages("job1")[0]["markdown"] == "# Example"
    Store(tmp_path)
    assert store.job("job1")["status"] == "completed"


def test_restart_marks_unfinished(tmp_path):
    store = Store(tmp_path)
    store.add_job("job2", "crawl", {"url":"https://example.org"}, 5)
    Store(tmp_path)
    assert store.job("job2")["status"] == "interrupted"
