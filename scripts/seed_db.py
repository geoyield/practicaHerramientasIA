from database import SessionLocal
from seed_data import seed_database


def main() -> None:
    with SessionLocal() as session:
        result = seed_database(session)
    print(
        "Semillas aplicadas: "
        f"{result['centers_created']} centros nuevos, "
        f"{result['classes_created']} clases nuevas."
    )


if __name__ == "__main__":
    main()
