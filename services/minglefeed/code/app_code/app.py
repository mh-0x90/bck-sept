import logging

from db import init_db
from internal_service import start_internal_service
from preview import start_worker
from web import run_web


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    init_db()
    start_internal_service()
    start_worker()
    run_web()


if __name__ == "__main__":
    main()
