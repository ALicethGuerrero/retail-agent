import subprocess
import sys

from app.db.postgres import init_db, use_mock_data


def main() -> int:
    if not use_mock_data():
        init_db()
    raise SystemExit(
        subprocess.call([sys.executable, "-m", "streamlit", "run", "ui.py"])
    )


if __name__ == "__main__":
    main()
