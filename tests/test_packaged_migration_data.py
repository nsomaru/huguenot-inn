from importlib import resources


def test_migration_data_is_available_as_package_resource() -> None:
    migrations = resources.files("huguenot.persistence").joinpath("migrations")
    assert migrations.joinpath("0001_initial.sql").is_file()
