"""Desktop SQLite auto-migration: old exe databases (NOT NULL weights)
are rebuilt preserving data, with a .bak backup."""
import sqlite3

from desktop import _migrate_sqlite, _sqlite_db_path


def _old_db(path):
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE print_history (id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "purity_huid VARCHAR(120) NOT NULL, product_name VARCHAR(120) NOT NULL,"
                "gross_weight NUMERIC(10, 3) NOT NULL, net_weight NUMERIC(10, 3) NOT NULL,"
                "copies INTEGER NOT NULL, printer_name VARCHAR(200) NOT NULL,"
                "template_version VARCHAR(50) NOT NULL, status VARCHAR(20) NOT NULL,"
                "error_message TEXT NOT NULL, printed_at DATETIME NOT NULL)")
    con.execute("INSERT INTO print_history (purity_huid, product_name, gross_weight,"
                "net_weight, copies, printer_name, template_version, status,"
                "error_message, printed_at) VALUES "
                "('18Kt HUID','Ring',2.146,2.146,1,'P','v5','success','','2026-01-01 00:00:00')")
    con.commit()
    con.close()


def test_migrate_sqlite_preserves_data(tmp_path):
    db = str(tmp_path / "old.db")
    _old_db(db)
    _migrate_sqlite(db)
    con = sqlite3.connect(db)
    cols = {r[1]: r[3] for r in con.execute("PRAGMA table_info(print_history)").fetchall()}
    assert cols["gross_weight"] == 0 and cols["net_weight"] == 0
    row = con.execute("SELECT purity_huid, gross_weight FROM print_history").fetchone()
    assert row[0] == "18Kt HUID" and float(row[1]) == 2.146
    con.close()
    import os

    assert os.path.isfile(db + ".bak")


def test_migrate_sqlite_skips_current(tmp_path):
    db = str(tmp_path / "new.db")
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE print_history (id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "gross_weight NUMERIC(10, 3), net_weight NUMERIC(10, 3))")
    con.commit()
    con.close()
    _migrate_sqlite(db)
    import os

    assert not os.path.isfile(db + ".bak")


def test_sqlite_db_path_absolute():
    assert _sqlite_db_path("sqlite:///C:/data/tagprinter.db") == "C:\\data\\tagprinter.db"
