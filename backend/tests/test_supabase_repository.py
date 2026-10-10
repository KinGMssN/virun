from app.repositories.transport_repository import (
    JsonTransportRepository,
    SupabaseTransportRepository,
)


class FakeQuery:
    def __init__(self, client, table):
        self.client = client
        self.table_name = table
        self.start = 0
        self.end = 0

    def select(self, _columns):
        return self

    def order(self, _column):
        return self

    def range(self, start, end):
        self.start = start
        self.end = end
        self.client.ranges.append((self.table_name, start, end))
        return self

    def execute(self):
        return type(
            "Response",
            (),
            {"data": self.client.tables[self.table_name][self.start:self.end + 1]},
        )()


class FakeSupabaseClient:
    def __init__(self, tables):
        self.tables = tables
        self.ranges = []

    def table(self, name):
        return FakeQuery(self, name)


def test_supabase_repository_reads_and_paginates_rows(monkeypatch):
    source = JsonTransportRepository()
    client = FakeSupabaseClient(
        {
            "transport_stops": [row.model_dump(mode="json") for row in source.list_stops()],
            "transport_options": [row.model_dump(mode="json") for row in source.list_options()],
        }
    )
    monkeypatch.setattr(SupabaseTransportRepository, "PAGE", 2)
    repository = SupabaseTransportRepository(client=client)

    assert repository.list_options() == source.list_options()
    assert repository.list_stops() == source.list_stops()
    assert repository.metadata()["dataset_label"] == "SUPABASE"
    assert ("transport_options", 0, 1) in client.ranges
    assert ("transport_options", 2, 3) in client.ranges
    assert ("transport_stops", 0, 1) in client.ranges
