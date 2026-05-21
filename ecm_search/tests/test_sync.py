from unittest.mock import MagicMock, patch

from app.sync import sync_once


def _doc(i, wd):
    return {
        "id": i, "name": f"f{i}.pdf", "ocr_text": "",
        "keywords": False, "entities": False,
        "document_type_id": False, "directory_id": False,
        "ocr_content_hash": False, "write_date": wd,
    }


def _state(checkpoint="2025-01-01 00:00:00", cycle=0):
    state = MagicMock()
    state.get_checkpoint.return_value = checkpoint
    state.get_cycle.return_value = cycle + 1
    return state


def test_sync_uses_inclusive_checkpoint_and_id_order():
    odoo = MagicMock()
    odoo.search_read.return_value = []
    sync_once(odoo, MagicMock(), MagicMock(), _state(), reconcile_every=12)
    domain = odoo.search_read.call_args[0][1]
    assert ["write_date", ">=", "2025-01-01 00:00:00"] in domain
    assert odoo.search_read.call_args[1]["order"] == "write_date asc, id asc"


def test_sync_pages_through_all_results():
    # first page full (200), second page partial -> two calls, all docs seen
    page1 = [_doc(i, "2025-03-01 10:00:00") for i in range(200)]
    page2 = [_doc(200 + i, "2025-03-01 10:00:01") for i in range(5)]
    odoo = MagicMock()
    odoo.search_read.side_effect = [page1, page2]
    state = _state()

    with patch("app.sync.index_doc", return_value=True) as idx:
        indexed = sync_once(odoo, MagicMock(), MagicMock(), state,
                            reconcile_every=12)

    assert odoo.search_read.call_count == 2
    assert odoo.search_read.call_args_list[0][1]["offset"] == 0
    assert odoo.search_read.call_args_list[1][1]["offset"] == 200
    assert idx.call_count == 205
    assert indexed == 205
    # checkpoint advanced to max write_date seen
    state.set_checkpoint.assert_called_once_with("2025-03-01 10:00:01")


def test_sync_counts_only_indexed_docs():
    docs = [_doc(1, "2025-03-01 10:00:00"), _doc(2, "2025-03-01 10:00:00")]
    odoo = MagicMock()
    odoo.search_read.return_value = docs
    with patch("app.sync.index_doc", side_effect=[True, False]):
        indexed = sync_once(odoo, MagicMock(), MagicMock(), _state(),
                            reconcile_every=12)
    assert indexed == 1


def test_sync_keeps_checkpoint_when_no_docs():
    odoo = MagicMock()
    odoo.search_read.return_value = []
    state = _state()
    sync_once(odoo, MagicMock(), MagicMock(), state, reconcile_every=12)
    state.set_checkpoint.assert_not_called()


def test_sync_reconciles_every_n_cycles():
    odoo = MagicMock()
    odoo.search_read.return_value = []
    odoo.search.return_value = []
    state = _state(cycle=11)  # get_cycle -> 12
    store = MagicMock()
    store.all_ids.return_value = []
    sync_once(odoo, MagicMock(), store, state, reconcile_every=12)
    odoo.search.assert_called_once()
