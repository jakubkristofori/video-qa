default:
    @just --list

install:
    python -m pip install -e ".[dev]"

lint:
    ruff check .

test:
    pytest -q

# Zkontroluje jednu nebo více epizod: just qa episodes/tutu-ep01
qa *EPISODES:
    video-qa {{EPISODES}}

# Lint + testy (to samé, co běží v CI)
check: lint test
