from main_batch_mode import main

if __name__ == "__main__":
    projects = ["auctions"]
    for project in projects:
        print(f"\nEseguo progetto {project}...")
        main(project)
