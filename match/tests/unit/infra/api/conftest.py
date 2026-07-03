import pytest
from sqlalchemy import text

from match.db import Session
from match.infra.api.security import hash_password

VALID_VERIF_CODE = "2f75ccc7-9f7d-45f3-87bf-44345b0f2f06"
SEED_PASSWORD = "s3cr3t-password"


@pytest.fixture(autouse=True)
def populate_db():
    session = Session()
    password_hash = hash_password(SEED_PASSWORD)
    clear_users_statement = "DELETE FROM users;"
    clear_statement = "DELETE FROM tasks;"
    session.execute(text(clear_users_statement))
    session.execute(text(clear_statement))
    users_statement = """
        INSERT OR REPLACE INTO users (
            id, first_name, last_name, email, properties, is_verified, verification_code, password_hash, created_at
        ) VALUES
            (100, 'John', 'Johnson', 'john@johnson.com', '[]', 1, :code_100, :pw, '2024-11-14T00:00:00Z'),
            (101, 'Adam', 'Adamson', 'adam@adamson.com', '[]', 1, :code_101, :pw, '2024-11-14T00:00:00Z'),
            (102, 'Gary', 'Moveout', 'gary@move.out', '[]', 0, :code_102, :pw, '2024-11-14T00:00:00Z'),
            (103, 'Garry', 'Moveout', 'garry@move.out', '[]', 0, :code_103, :pw, '2024-11-14T00:00:00Z');
        """
    statement = """
        INSERT OR REPLACE INTO tasks (id,title,description,status,category,owner_id,helper_id,updated_at,created_at,location_lat,location_lon,location_address)
        VALUES (100, 'Help', 'please help me', 'open', 'other', 100, null, null, '2024-11-14T00:00:00Z', 39.4738, 0.3756, 'My address');
        """
    session.execute(
        text(users_statement),
        {
            "code_100": "verif-code-100",
            "code_101": "verif-code-101",
            "code_102": "verif-code-102",
            "code_103": VALID_VERIF_CODE,
            "pw": password_hash,
        },
    )
    session.execute(text(statement))
    session.commit()
