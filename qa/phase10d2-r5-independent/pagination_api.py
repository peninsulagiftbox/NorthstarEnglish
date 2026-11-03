import datetime

from run import q


def set_due(count):
    q.sql("UPDATE concept_review_card SET due_at=DATE_ADD(UTC_TIMESTAMP(3), INTERVAL 32 DAY) WHERE owner_key='local'", label=f"due-reset-{count}")
    if count:
        q.sql(f"UPDATE concept_review_card SET due_at=UTC_TIMESTAMP(3) WHERE owner_key='local' ORDER BY due_at,id LIMIT {count}", label=f"due-set-{count}")
    actual = q.sql("SELECT COUNT(*) FROM concept_review_card WHERE owner_key='local' AND due_at<=UTC_TIMESTAMP(3)")
    assert actual == str(count), (count, actual)


def traverse(all_param, expected, limit=None):
    pages, items = [], []
    cursor = None
    while True:
        path = f"/concept-reviews/due?all={all_param}" + (f"&cursor={cursor}" if cursor else "") + (f"&limit={limit}" if limit else "")
        status, body = q.request(path)
        assert status == 200, (path, status, body)
        pages.append(body)
        items.extend(body["items"])
        cursor = body["nextCursor"]
        assert len(pages) < 130, "pagination did not terminate"
        if not cursor:
            break
    ids = [item["id"] for item in items]
    assert len(ids) == len(set(ids)) == expected, (len(ids), len(set(ids)), expected)
    keys = [(datetime.datetime.fromisoformat(item["dueAt"]), item["id"]) for item in items]
    assert keys == sorted(keys), "due pages are not globally ordered"
    return pages


def run_checks():
    results = {}
    for count in (0, 1, 20, 21, 22, 100):
        set_due(count)
        pages = traverse("false", count)
        results[f"due-{count}"] = {"pages": len(pages), "items": count}
        if count == 20:
            assert len(pages[0]["items"]) == 20 and pages[0]["nextCursor"], "20-card boundary must expose a cursor"
            assert pages[1]["items"] == [] and pages[1]["nextCursor"] is None, "cursor page after full boundary must be empty"
    set_due(100)
    results["all-limit100"] = {"pages": len(traverse("true", 101, limit=100))}
    results["all-limit20"] = {"pages": len(traverse("true", 101))}
    results["all-limit1"] = {"pages": len(traverse("true", 101, limit=1))}
    status, body = q.request("/concept-reviews/due?all=true&limit=101")
    assert status == 422, (status, body)
    results["limit-101-invalid"] = {"status": status}
    q.save("pagination-api-results.json", results)
    print("PAGINATION-API", results, flush=True)
