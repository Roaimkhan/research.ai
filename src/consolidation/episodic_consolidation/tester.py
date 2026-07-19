from src.consolidation.episodic_consolidation.graph import graph


def main():
    app = graph.compile()

    initial_state = {
        "raw_entries": [],
        "written_gist_ids": [],
        "embedded_gists": [],
        "errors": [],
    }

    result = app.invoke(initial_state)

    print("\n=== PIPELINE FINISHED ===")
    print("Written gists:", result.get("written_gist_ids"))
    print("Errors:", result.get("errors"))


if __name__ == "__main__":
    main()