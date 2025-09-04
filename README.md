# Instalation

curl -LsSf https://astral.sh/uv/install.sh | sh

git clone https://github.com/luciusb/robotour-org-py.git .

git checkout 2025

uv sync --managed-python

# Local testing

uv run flask --debug
