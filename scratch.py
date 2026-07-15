from langgraph.store.memory import InMemoryStore
import uuid

store = InMemoryStore()
nm = "mmaa"
store.put(nm, str(uuid.uuid4()), {"memory": "test"})
print(list(store.search(nm)))
